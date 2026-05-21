const express = require('express');
const cors = require('cors');
const multer = require('multer');
const sharp = require('sharp');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// مجلد مؤقت لحفظ نتائج الدمج حتى يتمكن التطبيق من تحميلها وحفظها
const RESULTS_DIR = path.join('/tmp', 'cookie-typer-results');

if (!fs.existsSync(RESULTS_DIR)) {
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
}

// إعداد multer لاستقبال الصور في الذاكرة (Buffer) مع حد أقصى للرفع 50 ميجابايت لكل طلب
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB للصورة الواحدة
    files: 20,
  },
  fileFilter: (req, file, cb) => {
    const allowedMimes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (allowedMimes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('يُسمح فقط بصور PNG و JPEG'), false);
    }
  },
});

// رابط تحميل مؤقت للصورة الناتجة
app.get('/results/:fileName', (req, res) => {
  const fileName = path.basename(req.params.fileName);
  const filePath = path.join(RESULTS_DIR, fileName);

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'الصورة غير موجودة أو انتهت صلاحيتها' });
  }

  res.setHeader('Content-Type', 'image/png');
  res.setHeader('Content-Disposition', `inline; filename="${fileName}"`);
  res.sendFile(filePath);
});

/**
 * نقطة النهاية: POST /merge
 * تستقبل عدة صور (حقل images) مع خيار unifyWidth (true/false)
 * تعيد رابط صورة PNG مدمجة بأعلى جودة (lossless) بعد حفظها مؤقتًا على الخادم
 */
app.post('/merge', upload.array('images', 20), async (req, res) => {
  try {
    const files = req.files;
    if (!files || files.length === 0) {
      return res.status(400).json({ error: 'يجب إرسال صورة واحدة على الأقل' });
    }

    // قراءة خيار توحيد العرض
    const unifyWidth = req.body.unifyWidth === 'true';

    // --- معالجة الصور باستخدام sharp مع الحفاظ على الجودة الأصلية ---
    const imageMetas = [];
    const sharpInstances = [];

    for (const file of files) {
      const instance = sharp(file.buffer);
      const metadata = await instance.metadata();
      imageMetas.push({
        width: metadata.width,
        height: metadata.height,
      });
      sharpInstances.push(instance);
    }

    // حساب العرض الأقصى إذا كان التوحيد مطلوبًا
    let maxWidth = 0;
    imageMetas.forEach((meta) => {
      if (meta.width > maxWidth) maxWidth = meta.width;
    });

    // حساب الارتفاع الإجمالي بعد توحيد العرض
    let totalHeight = 0;
    const sizes = imageMetas.map((meta) => {
      const targetWidth = unifyWidth ? maxWidth : meta.width;
      const targetHeight = Math.round((meta.height / meta.width) * targetWidth);
      totalHeight += targetHeight;
      return { width: targetWidth, height: targetHeight };
    });

    // إنشاء صورة فارغة بالحجم النهائي (شفافة)
    let compositeImage = sharp({
      create: {
        width: unifyWidth ? maxWidth : Math.max(...sizes.map(s => s.width)),
        height: totalHeight,
        channels: 4,
        background: { r: 0, g: 0, b: 0, alpha: 0 }, // خلفية شفافة
      },
    });

    // تجهيز عمليات الدمج (composite) لجميع الصور
    const compositeOps = [];
    let currentY = 0;

    for (let i = 0; i < sharpInstances.length; i++) {
      const meta = imageMetas[i];
      const targetSize = sizes[i];

      // تغيير حجم الصورة إلى الهدف
      const resized = sharpInstances[i].resize({
        width: targetSize.width,
        height: targetSize.height,
        fit: 'fill',
        withoutEnlargement: false, // السماح بالتكبير للحفاظ على الدقة
      });

      // تحويل إلى PNG لضمان الشفافية
      const pngBuffer = await resized.png().toBuffer();

      compositeOps.push({
        input: pngBuffer,
        top: currentY,
        left: 0,
      });

      currentY += targetSize.height;
    }

    // تنفيذ الدمج
    const mergedImage = await compositeImage
      .composite(compositeOps)
      .png({ compressionLevel: 0, palette: false }) // compressionLevel 0 = lossless
      .toBuffer();

    // حفظ الصورة الناتجة مؤقتًا على الخادم
    const fileName = `merged_${Date.now()}_${crypto.randomBytes(8).toString('hex')}.png`;
    const filePath = path.join(RESULTS_DIR, fileName);

    fs.writeFileSync(filePath, mergedImage);

    // حذف الصورة المؤقتة بعد 30 دقيقة
    setTimeout(() => {
      fs.unlink(filePath, (error) => {
        if (error && error.code !== 'ENOENT') {
          console.error('خطأ أثناء حذف الصورة المؤقتة:', error);
        }
      });
    }, 30 * 60 * 1000);

    const protocol = req.headers['x-forwarded-proto'] || req.protocol;
    const host = req.get('host');
    const resultUrl = `${protocol}://${host}/results/${fileName}`;

    // إرسال رابط الصورة الناتجة
    res.json({
      success: true,
      url: resultUrl,
      fileName,
      expiresInMinutes: 30,
    });
  } catch (error) {
    console.error('خطأ في الدمج:', error);
    res.status(500).json({ error: 'Fails' });
  }
});

// نقطة نهاية للتحقق من صحة الخادم
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`خادم دمج الصور يعمل على المنفذ ${PORT}`);
});