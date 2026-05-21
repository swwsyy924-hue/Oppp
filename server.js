const express = require('express');
const cors = require('cors');
const multer = require('multer');
const sharp = require('sharp');
const path = require('path');
const { v2: cloudinary } = require('cloudinary');

const app = express();
const PORT = process.env.PORT || 3000;

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
});

// Middleware
app.use(cors());
app.use(express.json());

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

/**
 * نقطة النهاية: POST /merge
 * تستقبل عدة صور (حقل images) مع خيار unifyWidth (true/false)
 * تعيد رابط صورة PNG مدمجة بأعلى جودة (lossless) بعد رفعها على Cloudinary
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
    // تحويل كل buffer إلى كائن sharp واستخراج البيانات الوصفية
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

      // تغيير حجم الصورة إلى الهدف (إذا كان التوحيد أو لم يكن، ولكننا نحتاج تغيير الحجم إذا كان العرض مختلفًا)
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
      .png({ compressionLevel: 0, palette: false }) // compressionLevel 0 = lossless, no compression artifacts
      .toBuffer();

    // رفع الصورة الناتجة إلى Cloudinary
    const cloudinaryResult = await new Promise((resolve, reject) => {
      const stream = cloudinary.uploader.upload_stream(
        {
          folder: 'cookie-typer/merged',
          resource_type: 'image',
          format: 'png',
        },
        (error, result) => {
          if (error) {
            return reject(error);
          }
          resolve(result);
        }
      );

      stream.end(mergedImage);
    });

    // إرسال رابط الصورة الناتجة
    res.json({
      success: true,
      url: cloudinaryResult.secure_url,
      publicId: cloudinaryResult.public_id,
      width: cloudinaryResult.width,
      height: cloudinaryResult.height,
      format: cloudinaryResult.format,
    });
  } catch (error) {
    console.error('خطأ في الدمج:', error);
    res.status(500).json({ error: 'فشل معالجة الصور على الخادم' });
  }
});

// نقطة نهاية للتحقق من صحة الخادم
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`خادم دمج الصور يعمل على المنفذ ${PORT}`);
});