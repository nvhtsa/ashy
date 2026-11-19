// Builds the thumbnail template PSD: art + tag plate as pixels, title and tag as
// live text layers so they stay retypeable in Photoshop.
//
// Run with:  node --experimental-default-type=commonjs build_psd.cjs
const fs = require('fs');
const path = require('path');
// `npm install ag-psd` in a scratch folder, or edit this path to wherever it lives.
const { writePsdBuffer, readPsd } = require(process.env.AG_PSD_PATH || 'ag-psd');

const HERE = __dirname;
const PSDDIR = path.join(HERE, 'psd');
const meta = JSON.parse(fs.readFileSync(path.join(PSDDIR, 'meta.json'), 'utf8'));

const W = 1280;
const H = 720;

function pixels(name) {
  const m = meta[name];
  return {
    width: m.width,
    height: m.height,
    data: new Uint8Array(fs.readFileSync(path.join(PSDDIR, `${name}.rgba`))),
  };
}

const offset = (name) => ({ left: meta[name].left || 0, top: meta[name].top || 0 });

const rgb = (r, g, b) => ({ r, g, b });
const CHARCOAL = rgb(20, 18, 26);
const SMOKE = rgb(233, 229, 221);
const IRIS = rgb(155, 138, 240);
const WHITE = rgb(255, 255, 255);

// A point-text layer. `baseline` is the y of the first line's baseline, which is
// what Photoshop treats as the text origin.
function textLayer({ name, text, x, baseline, size, leading, tracking, color, font }) {
  return {
    name,
    left: Math.round(x),
    top: Math.round(baseline - size * 0.86),
    right: Math.round(x + 900),
    bottom: Math.round(baseline + size * 0.3),
    text: {
      text,
      shapeType: 'point',
      pointBase: [0, 0],
      orientation: 'horizontal',
      antiAlias: 'smooth',
      transform: [1, 0, 0, 1, x, baseline],
      style: {
        font: { name: font },
        fontSize: size,
        fillColor: color,
        tracking,
        autoLeading: false,
        leading,
        autoKerning: true,
      },
      paragraphStyle: { justification: 'left' },
    },
  };
}

// Layer names stay ASCII: the PSD Pascal-string field mangles non-ASCII characters.
const art = { name: '1 - ART (replace this)', ...offset('art'), imageData: pixels('art') };
const plate = { name: '2 - TAG PLATE', ...offset('plate'), imageData: pixels('plate') };

// Brackets ride smaller than the letter, matching the images: .68em, lifted .12em.
// A single text layer can't size part of its string, so the brackets are style runs.
const markBase = textLayer({
  name: '3 - TAG MARK  [a]',
  text: '[a]',
  x: 72,
  baseline: 650,
  size: 26,
  leading: 26,
  tracking: 0,
  color: IRIS,
  font: 'Consolas',
});

const bracketRun = { font: { name: 'Consolas' }, fontSize: 18, baselineShift: 3, fillColor: IRIS };
const mark = {
  ...markBase,
  text: {
    ...markBase.text,
    styleRuns: [
      { length: 1, style: bracketRun },
      { length: 1, style: { font: { name: 'Consolas' }, fontSize: 26, fillColor: IRIS } },
      { length: 1, style: bracketRun },
    ],
  },
};

const label = textLayer({
  name: '4 - TAG LABEL',
  text: 'ZOMBIES · PART 1',
  x: 156,
  baseline: 649.5,
  size: 24,
  leading: 24,
  tracking: 140,
  color: SMOKE,
  font: 'Consolas',
});

const title = textLayer({
  name: '5 - TITLE',
  text: 'Der Eisendrache,\nagain',
  x: 51,
  baseline: 120.125,
  size: 95,
  leading: 90.25,
  tracking: -35,
  color: WHITE,
  // PostScript name of the Bold instance shipped in brand/fonts, so Photoshop
  // resolves the weight instead of guessing at a family default.
  font: 'BricolageGrotesque-Bold',
});

const psd = {
  width: W,
  height: H,
  children: [art, plate, mark, label, title],
  imageData: pixels('composite'),
  imageResources: {
    resolutionInfo: {
      horizontalResolution: 72,
      horizontalResolutionUnit: 'PPI',
      widthUnit: 'Inches',
      verticalResolution: 72,
      verticalResolutionUnit: 'PPI',
      heightUnit: 'Inches',
    },
  },
};

const buffer = writePsdBuffer(psd, { invalidateTextLayers: true });
const outPath = path.join(HERE, '..', 'ashtyn-thumbnail-template.psd');
fs.writeFileSync(outPath, buffer);
console.log('wrote', outPath, buffer.length, 'bytes');

// --- read back and report what a PSD reader actually sees ---
const back = readPsd(buffer, {
  skipLayerImageData: true,
  skipCompositeImageData: true,
  skipThumbnail: true,
});
console.log('canvas', back.width, 'x', back.height);
for (const layer of back.children) {
  const t = layer.text;
  console.log(
    `- ${layer.name.padEnd(24)} ${t ? `text(${JSON.stringify(t.text)}) size=${t.style && t.style.fontSize} font=${t.style && t.style.font && t.style.font.name}` : 'pixels'} bounds=${layer.left},${layer.top},${layer.right},${layer.bottom}`
  );
}
