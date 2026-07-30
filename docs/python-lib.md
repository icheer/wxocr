<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 影印版的pdf, 使用Node.js库进行图片提取, 推荐用哪些库?

对于影印版（扫描版）PDF，每一页本质上就是一张扫描图片嵌入在PDF对象里，所以"提取图片"通常有两种需求：**提取页面内嵌入的原始图片对象**，或者**把每一页整页渲染/转换成图片**（更常用，因为扫描PDF往往整页就是一张图）。下面按这两种场景推荐Node.js库。

## 页面渲染为图片（推荐用于影印版）

因为影印版PDF每页基本等同于一张扫描图，最稳妥的做法是把每页整体渲染成PNG/JPG，再做后续OCR或处理。

- **pdf.js（pdfjs-dist）**：Mozilla官方PDF渲染引擎，支持在Node.js中把每页渲染到canvas再导出图片，兼容性和渗透率最高，适合精细控制渲染分辨率。[^1_1][^1_2]
- **pdf2pic**：基于GraphicsMagick/Ghostscript，几行代码即可把PDF每页转成PNG，API简单，是很多人处理扫描PDF转图片再OCR的首选。[^1_2]
- **node-poppler（pdf-poppler）**：封装了poppler-utils的pdftoppm命令，转换速度快、图片质量稳定，适合批量处理大文件。[^1_3]


## 提取PDF内嵌图片对象

如果PDF中确实是以独立图片对象嵌入（而非整页栅格化），可以直接提取这些图片资源。

- **pdf-lib**：可以解析PDF结构、遍历页面资源字典，提取内嵌的图片对象，同时也支持编辑/合并PDF，功能全面且纯JS实现无需外部依赖。[^1_1]
- **pdfjs-dist（配合 getOperatorList）**：能读取页面渲染指令流，从中抓取图片XObject，适合需要精确控制提取哪些图片的场景。[^1_1]
- **IronPDF for Node.js**：商业库，提供 `extractRawImages()` 方法直接返回页面内所有原始图片的Buffer数组，代码简单但需要付费授权。[^1_4]


## 库选型对比

| 库 | 适用场景 | 依赖情况 | 特点 |
| :-- | :-- | :-- | :-- |
| pdf.js (pdfjs-dist) | 页面渲染/内嵌图提取 | 纯JS，无外部二进制依赖 | 官方维护，社区最大，灵活但API稍复杂[^1_1][^1_2] |
| pdf2pic | 整页转图片 | 需系统安装GraphicsMagick/Ghostscript | 上手最快，适合批量扫描PDF转图[^1_2] |
| node-poppler | 整页转图片，批量处理 | 需系统安装poppler-utils | 转换速度快、质量高，适合大文件[^1_3] |
| pdf-lib | 内嵌图片提取/PDF编辑 | 纯JS | 无需外部依赖，功能全面（读+写）[^1_1] |
| IronPDF | 内嵌图提取（商业） | 需付费授权+引擎包 | API简洁（extractRawImages），但非开源[^1_4] |

## 实际处理建议

对于影印版PDF，常见工作流是：用 **pdf2pic** 或 **node-poppler** 把每页转成高分辨率PNG，再配合 **Tesseract.js** 做OCR识别文字。如果你的PDF既有内嵌独立图片又想同时提取整页扫描图，建议先用pdf.js的`getOperatorList`判断页面结构（是单一大图还是多个图片对象拼接），再决定用整页渲染还是逐个图片提取的方案。[^1_5][^1_3][^1_1]

考虑到你的技术栈（Node.js/TS + Docker），如果需要大批量处理，pdf2pic/node-poppler在容器里配置好Ghostscript或poppler-utils后运行会比纯JS方案快很多，值得优先测试。
<span style="display:none">[^1_10][^1_11][^1_12][^1_13][^1_14][^1_15][^1_6][^1_7][^1_8][^1_9]</span>

<div align="center">⁂</div>

[^1_1]: https://juejin.cn/post/7478980680182218806

[^1_2]: https://blog.csdn.net/qq_35496811/article/details/145904227

[^1_3]: https://www.reddit.com/r/node/comments/129eym4/nlp_and_pdf_text_extract_in_nodejs/

[^1_4]: https://ironpdf.com/zh/nodejs/blog/using-ironpdf-for-nodejs/extract-image-node-js/

[^1_5]: https://cloud.tencent.com/developer/information/影印版pdf文字识别

[^1_6]: https://ironpdf.com/zh/nodejs/blog/using-ironpdf-for-nodejs/pdf-parser-node-tutorial/

[^1_7]: https://kb.aspose.cloud/zh/pdf/nodejs/extract-pictures-from-pdf-with-nodejs-rest-api/

[^1_8]: https://github.com/flyyuan/pdf2txt-chinese

[^1_9]: https://support.fuxinsoft.cn/?p=193

[^1_10]: https://blog.groupdocs.cloud/zh/parser/extract-images-from-pdf-files-using-node-js/

[^1_11]: https://www.freepdfconvert.com/zh-cn/extract-pdf-images

[^1_12]: https://www.youtube.com/watch?v=THauKA1p7po

[^1_13]: https://developer.aliyun.com/article/624814

[^1_14]: https://m.foxitsoftware.cn/function_page/45.html

[^1_15]: https://www.aneasystone.com/archives/2025/03/pdf-parser-libraries.html


---

# `判断页面结构（是单一大图还是多个图片对象拼接），再决定用整页渲染还是逐个图片提取的方案`  这两个步骤完全采用pdf.js能实现吗? 给一些示例代码

可以，pdf.js 完全能同时实现"判断页面结构"和"两种提取方式"，因为它提供了两个关键API：`page.getOperatorList()` 可以读出页面里所有绘图指令（包括图片对象及其变换矩阵/尺寸），`page.render()` 配合 node-canvas 可以整页栅格化。下面是完整的Node.js示例代码。[^2_1][^2_2]

## 环境准备

```bash
npm install pdfjs-dist canvas
```


## 第一步：分析页面结构，判断是单图还是多图拼接

利用 `getOperatorList()` 遍历指令流，抓取所有 `paintImageXObject`（图片）操作，同时结合当前的变换矩阵（transform）计算这张图片在页面坐标系中实际占据的宽高，再跟页面本身的宽高做比较。[^2_3][^2_1]

```javascript
const pdfjs = require('pdfjs-dist/legacy/build/pdf.js');

async function analyzePageStructure(page) {
  const viewport = page.getViewport({ scale: 1 });
  const pageWidth = viewport.width;
  const pageHeight = viewport.height;

  const ops = await page.getOperatorList();
  const images = [];
  let currentMatrix = [1, 0, 0, 1, 0, 0]; // 默认变换矩阵

  for (let i = 0; i < ops.fnArray.length; i++) {
    const fn = ops.fnArray[i];
    const args = ops.argsArray[i];

    // cm 指令：更新当前坐标变换矩阵（图片实际尺寸由它决定）
    if (fn === pdfjs.OPS.transform) {
      currentMatrix = args;
    }

    // paintImageXObject / paintJpegXObject：绘制图片
    if (fn === pdfjs.OPS.paintImageXObject || fn === pdfjs.OPS.paintJpegXObject) {
      const imgName = args[^2_0];
      // matrix[^2_0]、matrix[^2_3] 近似代表图片在页面上的实际宽高（单位与viewport一致）
      const drawnWidth = Math.abs(currentMatrix[^2_0]);
      const drawnHeight = Math.abs(currentMatrix[^2_3]);
      images.push({ name: imgName, drawnWidth, drawnHeight });
    }
  }

  const coverageRatios = images.map(img => {
    const areaRatio = (img.drawnWidth * img.drawnHeight) / (pageWidth * pageHeight);
    return { ...img, areaRatio };
  });

  // 判断逻辑：
  // 1. 只有1张图，且覆盖面积超过80%页面 -> 判定为"整页扫描图"（影印版典型特征）
  // 2. 有多张图，或单张图覆盖率较低 -> 判定为"多图拼接"，需逐个提取
  const isSinglePageScan =
    coverageRatios.length === 1 && coverageRatios[^2_0].areaRatio > 0.8;

  return {
    pageWidth,
    pageHeight,
    imageCount: coverageRatios.length,
    images: coverageRatios,
    strategy: isSinglePageScan ? 'FULL_PAGE_RENDER' : 'EXTRACT_INDIVIDUAL_IMAGES',
  };
}
```


## 第二步：根据判断结果分流处理

```javascript
const fs = require('fs');
const Canvas = require('canvas');

async function processPage(page, pageNum, outputDir) {
  const structure = await analyzePageStructure(page);
  console.log(`Page ${pageNum} strategy: ${structure.strategy}`, structure.images.length);

  if (structure.strategy === 'FULL_PAGE_RENDER') {
    await renderFullPage(page, pageNum, outputDir);
  } else {
    await extractIndividualImages(page, pageNum, outputDir);
  }
}

// 方案A：整页渲染（影印版扫描页常用）
async function renderFullPage(page, pageNum, outputDir) {
  const viewport = page.getViewport({ scale: 2.0 }); // 放大提高清晰度，利于后续OCR
  const canvas = Canvas.createCanvas(viewport.width, viewport.height);
  const context = canvas.getContext('2d');

  await page.render({ canvasContext: context, viewport }).promise;

  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(`${outputDir}/page-${pageNum}-full.png`, buffer);
}

// 方案B：逐个提取内嵌图片对象
async function extractIndividualImages(page, pageNum, outputDir) {
  // 必须先执行一次render，才能让 page.objs 里缓存实际的图片数据
  const viewport = page.getViewport({ scale: 1.0 });
  const canvas = Canvas.createCanvas(viewport.width, viewport.height);
  const context = canvas.getContext('2d');
  await page.render({ canvasContext: context, viewport }).promise;

  const ops = await page.getOperatorList();
  const imageNames = [];
  for (let i = 0; i < ops.fnArray.length; i++) {
    if (
      ops.fnArray[i] === pdfjs.OPS.paintImageXObject ||
      ops.fnArray[i] === pdfjs.OPS.paintJpegXObject
    ) {
      imageNames.push(ops.argsArray[i][^2_0]);
    }
  }

  let idx = 0;
  for (const name of imageNames) {
    await new Promise((resolve) => {
      page.objs.get(name, (imgObj) => {
        // imgObj 是包含 width/height/data(RGBA像素) 的对象
        const imgCanvas = Canvas.createCanvas(imgObj.width, imgObj.height);
        const imgCtx = imgCanvas.getContext('2d');
        const imageData = imgCtx.createImageData(imgObj.width, imgObj.height);
        imageData.data.set(imgObj.data);
        imgCtx.putImageData(imageData, 0, 0);

        const buf = imgCanvas.toBuffer('image/png');
        fs.writeFileSync(`${outputDir}/page-${pageNum}-img-${idx}.png`, buf);
        idx++;
        resolve();
      });
    });
  }
}
```


## 第三步：主流程整合

```javascript
async function main(pdfPath, outputDir) {
  const data = fs.readFileSync(pdfPath);
  const pdfDoc = await pdfjs.getDocument({ data }).promise;

  for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
    const page = await pdfDoc.getPage(pageNum);
    await processPage(page, pageNum, outputDir);
  }
}

main('./scanned-book.pdf', './output');
```


## 关键注意点

- `paintImageXObject` 拿到的 `imgObj.data` 是解码后的原始像素（RGBA），不是压缩格式，如果图片是JPEG压缩的，这种方式会丢失原始压缩质量，如果需要保留原图字节流最好还是走 pdf-lib 直接读PDF对象流。[^2_1]
- node-canvas 在某些环境（如Alpine Docker镜像）安装容易踩坑，需要提前装好Cairo等系统依赖，你在Docker容器里跑之前建议先本地验证一遍。[^2_4]
- `getOperatorList()` 里的变换矩阵计算图片实际尺寸只是近似估算，如果PDF有嵌套的Form XObject或复杂的裁剪路径，判断逻辑需要额外处理这些情况，实际生产环境建议先跑一批样本PDF人工核对判断准确率。[^2_3]

这套代码基本能满足你说的"先判断结构、再选择处理方案"的完整闭环，纯pdf.js + node-canvas无需其他外部二进制依赖，比较适合塞进你现有的Docker环境里跑批量任务。
<span style="display:none">[^2_10][^2_11][^2_12][^2_13][^2_14][^2_15][^2_5][^2_6][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://juejin.cn/post/7284433532075524151

[^2_2]: https://dev.to/yashnarkhedkar/how-to-convert-pdf-pages-to-images-in-nodejs-2a6k

[^2_3]: https://github.com/mozilla/pdf.js/discussions/18410

[^2_4]: https://github.com/mozilla/pdf.js/issues/17188

[^2_5]: https://mozilla.github.io/pdf.js/examples/

[^2_6]: https://mozilla.github.io/pdf.js/getting_started/

[^2_7]: https://www.ujcms.com/articles/63304513505454593.html

[^2_8]: https://stackoverflow.com/questions/79579312/cant-render-a-pdf-page-on-node-canva-nodejs-pdfjs-dist

[^2_9]: https://adg.csdn.net/695331765b9f5f31781bc17d.html

[^2_10]: https://rossta.net/blog/building-a-pdf-viewer-with-vue-part-1.html

[^2_11]: https://www.cnblogs.com/architectforest/p/16514022.html

[^2_12]: https://www.youtube.com/watch?v=sstkxOkAbeo

[^2_13]: https://www.nutrient.io/blog/complete-guide-to-pdfjs/

[^2_14]: https://www.nutrient.io/blog/how-to-build-a-javascript-pdf-viewer-with-pdfjs/

[^2_15]: https://apryse.com/blog/pdfjs/how-to-use-pdf-js


---

# 如果pdf的整页转变成图片后, 每一页上有浅色水印例如(\#ffd9d9),  pdf有效信息--文字颜色是黑色(例如\#1e1e1e),  是否有办法通过node.js对特定颜色的色值进行去色处理, 以便更好的ocr识别?

可以，用 **sharp** 库操作原始像素（raw pixel）数据是最直接的方案，通过读取每个像素的RGB值、判断是否接近水印色（\#ffd9d9这种浅色），再把它替换成白色，同时保留深色文字（\#1e1e1e），就能有效提升OCR识别率。[^3_1][^3_2]

## 核心思路

水印颜色（\#ffd9d9）和文字颜色（\#1e1e1e）在亮度和色相上差异很大——水印是浅粉色（高亮度、低饱和度），文字是接近黑色（低亮度）。可以利用这个亮度差做阈值判断，而不需要精确匹配某个具体色值，这样即使水印颜色有轻微渐变或抗锯齿边缘，也能被覆盖清除。

## 方案一：基于颜色距离的去水印（推荐，更精准）

计算每个像素与目标水印色的欧氏距离，在容差范围内的像素替换为白色，这样能保留文字的黑色像素不受影响。

```javascript
const sharp = require('sharp');

async function removeWatermarkByColor(inputPath, outputPath, options = {}) {
  const {
    watermarkColor = { r: 0xff, g: 0xd9, b: 0xd9 }, // #ffd9d9
    tolerance = 40, // 颜色距离容差，越大越激进
  } = options;

  const { data, info } = await sharp(inputPath)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const { width, height, channels } = info;

  for (let i = 0; i < data.length; i += channels) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];

    // 计算与水印色的欧氏距离
    const distance = Math.sqrt(
      Math.pow(r - watermarkColor.r, 2) +
      Math.pow(g - watermarkColor.g, 2) +
      Math.pow(b - watermarkColor.b, 2)
    );

    if (distance <= tolerance) {
      data[i] = 255;     // R -> 白色
      data[i + 1] = 255; // G
      data[i + 2] = 255; // B
    }
  }

  await sharp(data, { raw: { width, height, channels } })
    .png()
    .toFile(outputPath);
}

removeWatermarkByColor('./page-1-full.png', './page-1-clean.png', {
  tolerance: 35,
});
```


## 方案二：基于亮度阈值的二值化（更激进，OCR友好）

如果目标是最大化OCR识别率，更好的做法往往不是单纯"去水印"，而是直接把图片二值化——只保留深色文字为黑色，其他一切（包括水印）全部变白。这正好利用了 sharp 内置的 `threshold()` 方法。[^3_3]

```javascript
const sharp = require('sharp');

async function binarizeForOCR(inputPath, outputPath, thresholdValue = 150) {
  await sharp(inputPath)
    .greyscale()
    .threshold(thresholdValue) // 高于阈值->255白, 低于->0黑
    .toFile(outputPath);
}

binarizeForOCR('./page-1-full.png', './page-1-binary.png', 150);
```

这个方法的原理是：先转灰度，\#1e1e1e 换算成灰度大约是30（很暗），\#ffd9d9 换算成灰度大约是225（很亮），两者差距巨大，所以只要阈值设在150左右这两种颜色就能被完美分开。[^3_3]

## 方案三：结合HSL做更精细的水印识别（水印颜色不均匀时）

如果水印在扫描过程中因为压缩失真导致颜色有波动（不是纯\#ffd9d9，而是一片相近的浅粉色调），单纯RGB距离可能不够稳健，可以转换到HSL空间用饱和度+亮度双重判断。

```javascript
function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0, s = 0;
  const d = max - min;
  if (d !== 0) {
    s = d / (1 - Math.abs(2 * l - 1));
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60;
    if (h < 0) h += 360;
  }
  return { h, s: s * 100, l: l * 100 };
}

async function removeWatermarkByHSL(inputPath, outputPath) {
  const { data, info } = await sharp(inputPath)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const { width, height, channels } = info;

  for (let i = 0; i < data.length; i += channels) {
    const { s, l } = rgbToHsl(data[i], data[i + 1], data[i + 2]);
    // 水印特征：亮度很高(L>75%)，饱和度较低(S<40%) —— 浅粉色典型区间
    if (l > 75 && s < 40) {
      data[i] = 255;
      data[i + 1] = 255;
      data[i + 2] = 255;
    }
  }

  await sharp(data, { raw: { width, height, channels } })
    .png()
    .toFile(outputPath);
}
```


## 实际推荐流程

对于影印版PDF批量OCR处理，建议按下面顺序组合使用，效果和效率最佳：

- 先用方案二（灰度+阈值二值化）做第一轮清理，因为它计算最快，且对纯色浅色水印效果最直接。[^3_3]
- 如果文档背景不均匀或水印和文字颜色对比不够极端，再叠加方案一（颜色距离）做定向清除，作为二值化前的预处理步骤。
- 阈值参数不要写死，建议先对一小批样本页面跑一遍测试，用 `sharp().stats()` 获取图片的通道统计信息，动态确定最佳阈值，因为不同批次扫描件的曝光度可能有差异。[^3_4]


## 完整处理流水线示例

```javascript
async function preprocessForOCR(inputPath, outputPath) {
  await sharp(inputPath)
    .removeAlpha()
    .greyscale()
    .normalize() // 自动拉伸对比度，让文字更黑、背景更白
    .threshold(150)
    .toFile(outputPath);
}
```

`normalize()` 会先自动增强对比度，让原本偏灰的文字更接近纯黑，浅色水印更接近纯白，再配合 `threshold()` 二值化，通常比直接固定阈值效果更稳定。这套流程处理完之后再送进 Tesseract.js 做OCR，识别准确率会有明显提升。[^3_5]
<span style="display:none">[^3_10][^3_11][^3_12][^3_13][^3_14][^3_15][^3_6][^3_7][^3_8][^3_9]</span>

<div align="center">⁂</div>

[^3_1]: https://stackoverflow.com/questions/54847139/how-to-read-buffer-data-of-image-returned-by-sharp

[^3_2]: https://www.thealteroffice.com/blog/how-to-manipulate-image-pixels-using-node-js-and-sharp

[^3_3]: https://sharp.pixelplumbing.com/api-operation/

[^3_4]: https://www.npmjs.com/package/sharp

[^3_5]: https://sharp.nodejs.cn/api-operation/

[^3_6]: https://sharp.pixelplumbing.com/

[^3_7]: https://github.com/lovell/sharp/issues/1648

[^3_8]: https://developer.aliyun.com/article/597336

[^3_9]: https://blog.logrocket.com/processing-images-sharp-node-js/

[^3_10]: https://www.digitalocean.com/community/tutorials/how-to-process-images-in-node-js-with-sharp

[^3_11]: https://www.youtube.com/watch?v=107-BSLMwnw

[^3_12]: https://cloud.tencent.com/developer/article/1418083

[^3_13]: https://npmjs.com/package/sharp-cli

[^3_14]: https://hailangya.com/articles/2021/07/13/node-watermark/

[^3_15]: https://shillehtek.com/blogs/news/nodejs-sharp-edit-pixels-export-png


---

# 影印版的扫描件，有时候会有轻微的旋转，有办法使用node.js库来识别这种偏转角度并予以纠正吗？

这类问题属于图像"轻微倾斜纠正"（deskew），跟PDF页面整页旋转90/180/270度是完全不同的技术——需要先检测出精确的倾斜角度（比如0.5°、-2.3°这种小数），再做仿射旋转纠正。Node.js生态里没有像sharp那样"开箱即用"的deskew函数，但可以通过下面几种方式实现。[^4_1][^4_2]

## 方案一：opencv4nodejs（最强大，推荐）

OpenCV原生支持霍夫直线变换（Hough Transform），这是检测文档倾斜角度最经典的算法——通过检测图片中文字行形成的水平线簇，计算它们的平均角度偏差。

```bash
npm install opencv4nodejs
```

```javascript
const cv = require('opencv4nodejs');

function detectSkewAngle(imagePath) {
  const img = cv.imread(imagePath);
  const gray = img.bgrToGray();

  // 二值化 + 边缘检测
  const binary = gray.threshold(150, 255, cv.THRESH_BINARY_INV);
  const edges = binary.canny(50, 150);

  // 霍夫直线检测
  const lines = edges.houghLinesP(1, Math.PI / 180, 100, 100, 10);

  const angles = [];
  lines.forEach((line) => {
    const dx = line.x2 - line.x1;
    const dy = line.y2 - line.y1;
    const angle = Math.atan2(dy, dx) * (180 / Math.PI);
    // 只保留接近水平的线（文字行特征），排除竖线干扰
    if (Math.abs(angle) < 45) {
      angles.push(angle);
    }
  });

  // 取中位数作为最终倾斜角度，比平均值更抗噪声干扰
  angles.sort((a, b) => a - b);
  const median = angles[Math.floor(angles.length / 2)] || 0;
  return median;
}

function deskewImage(inputPath, outputPath) {
  const img = cv.imread(inputPath);
  const angle = detectSkewAngle(inputPath);

  const center = new cv.Point2(img.cols / 2, img.rows / 2);
  const rotationMatrix = cv.getRotationMatrix2D(center, angle, 1.0);

  const rotated = img.warpAffine(
    rotationMatrix,
    new cv.Size(img.cols, img.rows),
    cv.INTER_LINEAR,
    cv.BORDER_CONSTANT,
    new cv.Vec3(255, 255, 255) // 空白区域填充白色
  );

  cv.imwrite(outputPath, rotated);
  console.log(`Detected angle: ${angle.toFixed(2)}°, corrected.`);
}

deskewImage('./page-1-binary.png', './page-1-deskewed.png');
```


## 方案二：Projection Profile算法（纯JS实现，无需OpenCV）

如果你不想引入OpenCV这种较重的原生依赖（尤其在Docker多平台构建时opencv4nodejs编译经常踩坑），可以用"投影轮廓法"手写一个轻量级检测器：把图片旋转多个候选小角度，统计每个角度下水平投影的方差，方差最大的角度往往对应文字行排列最整齐的状态。

```javascript
const sharp = require('sharp');

async function detectSkewByProjection(imagePath, angleRange = 5, step = 0.2) {
  const { data, info } = await sharp(imagePath)
    .greyscale()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const { width, height } = info;
  let bestAngle = 0;
  let maxVariance = -Infinity;

  for (let angle = -angleRange; angle <= angleRange; angle += step) {
    const variance = await computeProjectionVariance(imagePath, angle);
    if (variance > maxVariance) {
      maxVariance = variance;
      bestAngle = angle;
    }
  }
  return bestAngle;
}

async function computeProjectionVariance(imagePath, angle) {
  const rotatedBuffer = await sharp(imagePath)
    .rotate(angle, { background: '#ffffff' })
    .greyscale()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const { data, info } = rotatedBuffer;
  const { width, height } = info;

  const rowSums = new Array(height).fill(0);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const pixel = data[y * width + x];
      if (pixel < 128) rowSums[y]++; // 统计黑色像素数(文字)
    }
  }

  const mean = rowSums.reduce((a, b) => a + b, 0) / rowSums.length;
  const variance =
    rowSums.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / rowSums.length;
  return variance;
}

async function autoDeskew(inputPath, outputPath) {
  const angle = await detectSkewByProjection(inputPath, 5, 0.5);
  console.log(`Detected skew angle: ${angle}°`);

  await sharp(inputPath)
    .rotate(angle, { background: '#ffffff' })
    .toFile(outputPath);
}

autoDeskew('./page-1-binary.png', './page-1-deskewed.png');
```

这个方案的原理是：文字行水平排列整齐时，逐行统计黑色像素数量会形成明显的"波峰波谷"（文字行vs行间空白），方差最大；一旦图片有倾斜，这种波动会被"抹平"，方差降低。它比OpenCV慢很多（要试很多角度），但胜在纯JS、无外部编译依赖，容器化部署更省心。

## 方案三：直接依赖Tesseract自带的deskew

Tesseract OCR引擎底层用的Leptonica库其实自带倾斜检测和自动纠正功能，某些配置下OCR识别时会自动处理小角度倾斜，不需要你单独写代码。

```javascript
const Tesseract = require('tesseract.js');

async function ocrWithAutoDeskew(imagePath) {
  const result = await Tesseract.recognize(imagePath, 'chi_sim', {
    tessedit_ocr_engine_mode: 1,
  });
  return result.data.text;
}
```

不过Tesseract.js（纯JS版）对倾斜的容忍度比C++原生的tesseract低很多，如果倾斜角度超过2-3度，识别率还是会明显下降，建议不要完全依赖它，最好提前用方案一或方案二做显式纠偏。

## 选型建议

| 方案 | 精度 | 速度 | 部署复杂度 |
| :-- | :-- | :-- | :-- |
| opencv4nodejs (霍夫变换) | 高，专为文档场景优化 | 快 | 高，需要编译原生依赖，Docker多阶段构建配置繁琐 |
| Projection Profile (纯sharp) | 中等，依赖角度搜索精细度 | 较慢（需多次旋转试算） | 低，零外部依赖 |
| Tesseract内置deskew | 低到中等，仅适合<3度小角度 | 快（集成在OCR流程里） | 低，已有tesseract.js即可用 |

考虑到你的技术栈已经在用Docker，如果对精度要求高，我建议直接上opencv4nodejs，把编译好的镜像缓存下来复用，一次配置好之后长期收益更大；如果只是轻量级需求或者不想折腾原生依赖，Projection Profile方案配合sharp已经能覆盖大多数"轻微倾斜（±5度内）"场景。
<span style="display:none">[^4_3][^4_4][^4_5][^4_6][^4_7][^4_8]</span>

<div align="center">⁂</div>

[^4_1]: https://www.convertapi.com/pdf-to-rotate/nodejs

[^4_2]: https://ironpdf.com/zh-hant/nodejs/examples/pdf-page-orientation/

[^4_3]: https://thecodebarbarian.com/working-with-pdfs-in-node-js.html

[^4_4]: https://blog.groupdocs.cloud/zh/merger/how-to-rotate-pdf-pages-using-rest-api-in-node-js/

[^4_5]: https://strapi.io/blog/7-best-javascript-pdf-parsing-libraries-nodejs-2025

[^4_6]: https://www.adobe.com/tw/acrobat/online/rotate-pdf.html

[^4_7]: https://www.reddit.com/r/node/comments/1mwh7ay/i_wrote_a_detailed_guide_on_generating_pdfs_from/

[^4_8]: https://products.groupdocs.com/zh/merger/nodejs-java/rotate/pdf/


---

# 如果技术栈从Node.js变为Python(>=3.12), 上述的"识别每页图片覆盖率决定抽取图片or渲染成整张图进行ocr" \& 指定色值的水印消除(或者有可能自动识别水印吗?) \& 识别图片倾斜程度并纠正, 这些lib推荐用哪些?

Python生态在这三个任务上比Node.js成熟得多，尤其是PyMuPDF和OpenCV几乎是文档处理的行业标准组合。下面按你三个需求逐一给出推荐库和示例代码。[^5_1][^5_2]

## 一、判断页面结构（单图 vs 多图拼接）+ 提取/渲染

**PyMuPDF (fitz)** 是Python处理PDF最强的库，直接提供 `page.get_images()` 获取图片列表及尺寸信息，同时 `page.get_pixmap()` 可以整页渲染，两者API都非常简洁，比Node.js的pdfjs方案简单得多。[^5_2][^5_1]

```python
import fitz  # PyMuPDF

def analyze_and_process(pdf_path, output_dir):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_rect = page.rect
        page_area = page_rect.width * page_rect.height

        image_list = page.get_images(full=True)
        images_info = []
        for img in image_list:
            xref = img[^5_0]
            for img_rect in page.get_image_rects(xref):
                area_ratio = (img_rect.width * img_rect.height) / page_area
                images_info.append({"xref": xref, "area_ratio": area_ratio})

        is_single_scan = (
            len(images_info) == 1 and images_info[^5_0]["area_ratio"] > 0.8
        )

        if is_single_scan:
            # 策略A：整页渲染（推荐用于影印版扫描页）
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 放大2倍提高清晰度
            pix.save(f"{output_dir}/page-{page_num+1}-full.png")
        else:
            # 策略B：逐个提取内嵌图片对象
            for img in image_list:
                xref = img[^5_0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:  # 处理CMYK等特殊色彩空间
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                pix.save(f"{output_dir}/page-{page_num+1}-img-{xref}.png")

analyze_and_process("./scanned-book.pdf", "./output")
```

PyMuPDF比pdf.js方案的优势在于原生C++内核（MuPDF），处理速度快很多，而且 `get_image_rects()` 直接给出图片在页面坐标系中的实际渲染尺寸，不需要像Node.js那样手动解析变换矩阵。[^5_3]

## 二、水印去除（指定色值 + 自动识别）

**指定色值去除**：用 **OpenCV (opencv-python)** 或 **Pillow + NumPy** 做像素级颜色距离/阈值处理，逻辑跟之前Node.js方案一致，但NumPy的向量化运算比手写像素循环快得多。

```python
import cv2
import numpy as np

def remove_watermark_by_color(input_path, output_path, watermark_bgr=(217, 217, 255), tolerance=40):
    img = cv2.imread(input_path)
    watermark = np.array(watermark_bgr, dtype=np.float64)

    diff = img.astype(np.float64) - watermark
    distance = np.sqrt(np.sum(diff ** 2, axis=2))

    mask = distance <= tolerance
    img[mask] = [255, 255, 255]

    cv2.imwrite(output_path, img)

remove_watermark_by_color("./page-1-full.png", "./page-1-clean.png")
```

**自动识别水印（不需要预先指定色值）**：这才是Python相比Node.js真正的优势所在，因为有成熟的图像修复算法可用。思路是利用水印通常"低对比度、覆盖大面积、颜色分布集中"的统计特征去自动检测。

```python
import cv2
import numpy as np

def auto_detect_watermark_mask(image_path, saturation_thresh=40, lightness_thresh=190):
    img = cv2.imread(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # 自动检测特征：高亮度(接近白) + 低饱和度(浅色调)，但非纯白背景
    mask = (v > lightness_thresh) & (v < 253) & (s < saturation_thresh) & (s > 5)
    mask = mask.astype(np.uint8) * 255

    # 形态学操作，去除孤立噪点，让水印区域连成一片
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask

def auto_remove_watermark(input_path, output_path):
    img = cv2.imread(input_path)
    mask = auto_detect_watermark_mask(input_path)

    # 使用图像修复算法(inpainting)，比单纯涂白更自然，边缘不生硬
    result = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    cv2.imwrite(output_path, result)

auto_remove_watermark("./page-1-full.png", "./page-1-auto-clean.png")
```

`cv2.inpaint()` 是关键——它不只是简单涂白，而是根据周围像素智能"填补"被标记区域，对于水印穿过文字笔画的情况效果比直接涂白更好，能避免破坏文字笔画的连续性。如果水印色值固定且已知（如你的\#ffd9d9场景），直接用方案一效率更高更可控；如果同一批文档水印颜色/位置不固定，自动检测+inpainting更实用。[^5_4][^5_5]

## 三、倾斜检测与纠正（deskew）

Python有一个专门的开源库叫 **deskew**，基于Radon变换，比手写OpenCV霍夫直线检测更简单可靠，是文档处理领域被广泛验证的方案。[^5_6]

```python
# pip install deskew scikit-image opencv-python

from skimage import io
from skimage.transform import rotate
from skimage.color import rgb2gray
from deskew import determine_skew
import numpy as np

def deskew_image(input_path, output_path):
    image = io.imread(input_path)
    grayscale = rgb2gray(image)
    angle = determine_skew(grayscale)

    print(f"Detected skew angle: {angle:.2f}°")
    rotated = rotate(image, angle, resize=True, cval=1, mode='constant') * 255
    io.imsave(output_path, rotated.astype(np.uint8))
    return angle

deskew_image("./page-1-clean.png", "./page-1-deskewed.png")
```

如果想要更可控、基于轮廓分析的方案（跟之前Node.js思路一致但用OpenCV原生实现，速度更快），可以用 `minAreaRect` 检测文字行轮廓角度取中位数。[^5_7][^5_8]

```python
import cv2
import numpy as np

def detect_and_correct_skew(input_path, output_path):
    img = cv2.imread(input_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 0)

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    dilated = cv2.dilate(binary, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    angles = []
    for contour in contours:
        if cv2.contourArea(contour) < 100:
            continue
        rect = cv2.minAreaRect(contour)
        angle = rect[-1]
        if angle not in (0.0, 90.0, -0.0):
            angles.append(angle)

    angles.sort()
    median_angle = angles[len(angles) // 2] if angles else 0
    if median_angle > 45:
        median_angle = -(90 - median_angle)

    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), median_angle, 1)
    deskewed = cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))
    cv2.imwrite(output_path, deskewed)
    print(f"Corrected angle: {median_angle:.2f}°")

detect_and_correct_skew("./page-1-clean.png", "./page-1-final.png")
```


## 库选型总结

| 任务 | 推荐库 | 优势 |
| :-- | :-- | :-- |
| PDF结构分析/图片提取/整页渲染 | PyMuPDF (fitz) | C++内核速度快，API简洁，一个库覆盖全部需求[^5_1][^5_2] |
| 指定色值去水印 | OpenCV + NumPy | 向量化运算快，逻辑直观 |
| 自动识别去水印 | OpenCV (HSV分割 + inpaint) | 无需预知颜色，inpainting修复更自然[^5_4] |
| 倾斜检测纠正（简单场景） | deskew (基于Radon变换) | 专用库，一行代码搞定，稳定性高[^5_6] |
| 倾斜检测纠正（可控场景） | OpenCV (minAreaRect + warpAffine) | 可精细调参，速度快，适合批量处理[^5_7][^5_8] |

## 完整处理流水线

三步串联起来的推荐顺序是：先用PyMuPDF判断结构并提取/渲染，再用OpenCV去水印，最后用deskew库纠偏，之后再送进OCR（如PaddleOCR或Tesseract）。这套组合几乎是文档数字化流水线的标准配置，社区案例和文档也远比Node.js生态丰富，长期维护成本会更低。

考虑到你已经熟悉Docker部署，PyMuPDF和OpenCV都有现成的轻量Python基础镜像可用，不像opencv4nodejs那样在Node.js里经常遇到原生编译的坑，这也是切换到Python栈处理这类图像密集型任务的一个实际收益。
<span style="display:none">[^5_10][^5_11][^5_12][^5_13][^5_14][^5_15][^5_9]</span>

<div align="center">⁂</div>

[^5_1]: https://pymupdf.readthedocs.io/en/latest/document.html

[^5_2]: https://blog.csdn.net/weixin_40959890/article/details/138472923

[^5_3]: https://artifex.com/blog/pymupdf-explored-image-handling-in-pdf

[^5_4]: https://cloud.baidu.com/article/3276577

[^5_5]: https://cloud.tencent.com/developer/article/2215953

[^5_6]: https://stackoverflow.com/questions/63164341/improving-image-deskew-using-python-and-opencv

[^5_7]: http://devblogs.damingsoft.com/deskew-scanned-document/

[^5_8]: https://www.dynamsoft.com/codepool/deskew-scanned-document.html

[^5_9]: https://blog.csdn.net/hzxOnlineOk/article/details/138276551

[^5_10]: https://support.i-search.com.cn/article/1569221687653

[^5_11]: https://juejin.cn/post/7348463942404702249

[^5_12]: https://cloud.tencent.com/developer/article/1866337

[^5_13]: https://gist.github.com/zabir-nabil/dfb78f584947ebdb9f29d39c9737b5c6

[^5_14]: https://www.aidoczh.com/pymupdf/changes.html

[^5_15]: https://juejin.cn/post/7295750874181287987

