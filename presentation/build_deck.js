const path = require('path');
const pptxgen = require('pptxgenjs');
const { applyTheme } = require('/home/aamanprime/.claude/skills/synced/360024ab-512d-4614-9be3-65a8eb698679_564ad0ce-65ef-418c-949d-b4d54a420299/pptx/scripts/apply_theme.js');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Aayush Gupta; Saksham Mishra; Shaman Ranjan; Aaman Sheikh; M Rayhan Khan';
pptx.company = 'IIIT-Delhi';
pptx.subject = 'Robotics course project: physics-informed inverse dynamics for reacher tracking';
pptx.title = 'Physics-Informed Inverse Dynamics for Reacher Arm Tracking';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Cambria',
  bodyFontFace: 'Arial',
  lang: 'en-US',
};

const THEME = {
  name: 'Reacher Robotics',
  headFontFace: 'Cambria',
  bodyFontFace: 'Arial',
  colors: {
    dk1: '10242A',
    lt1: 'F8FBFB',
    dk2: '23434A',
    lt2: 'E7F3F1',
    accent1: '00A896',
    accent2: 'F4A261',
    accent3: 'E76F51',
    accent4: '2A9D8F',
    accent5: '84A98C',
    accent6: '577590',
    hlink: '007C73',
    folHlink: '6B4B7A',
  },
};

const C = pptx.SchemeColor;
const S = pptx.ShapeType;
const CH = pptx.ChartType;
const W = 13.333;
const H = 7.5;
const ROOT = path.resolve(__dirname, '..');
const OUTPUT = path.join(__dirname, 'output', 'Reacher_Inverse_Dynamics_Project_Presentation.pptx');
const REACHER_IMAGE = path.join(__dirname, 'assets', 'reacher_render.png');

function freshShadow(opacity = 0.14, blur = 2, distance = 1.2) {
  return {
    type: 'outer',
    color: THEME.colors.dk1,
    opacity,
    blur,
    angle: 45,
    distance,
  };
}

function addText(slide, text, x, y, w, h, options = {}) {
  slide.addText(text, {
    x, y, w, h,
    isTextBox: true,
    margin: 0,
    fontFace: options.fontFace || 'Arial',
    fontSize: options.fontSize || 16,
    color: options.color || C.text1,
    bold: options.bold || false,
    italic: options.italic || false,
    align: options.align || 'left',
    valign: options.valign || 'mid',
    breakLine: options.breakLine,
    fit: options.fit || 'shrink',
    paraSpaceAfterPt: options.paraSpaceAfterPt,
    lineSpacingMultiple: options.lineSpacingMultiple,
    charSpacing: options.charSpacing,
    transparency: options.transparency,
    objectName: options.objectName,
  });
}

function addRichText(slide, runs, x, y, w, h, options = {}) {
  slide.addText(runs, {
    x, y, w, h,
    isTextBox: true,
    margin: options.margin === undefined ? 0 : options.margin,
    fontFace: options.fontFace || 'Arial',
    fontSize: options.fontSize || 16,
    color: options.color || C.text1,
    valign: options.valign || 'mid',
    align: options.align || 'left',
    breakLine: false,
    fit: 'shrink',
    objectName: options.objectName,
  });
}

function addCard(slide, x, y, w, h, options = {}) {
  slide.addShape(S.roundRect, {
    x, y, w, h,
    rectRadius: 0.08,
    fill: { color: options.fill || C.background1, transparency: options.transparency || 0 },
    line: { color: options.line || C.background2, width: options.lineWidth || 1 },
    shadow: options.shadow === false ? undefined : freshShadow(options.shadowOpacity || 0.10, 1.5, 0.9),
    objectName: options.objectName,
  });
}

function addPill(slide, text, x, y, w, options = {}) {
  slide.addShape(S.roundRect, {
    x, y, w, h: options.h || 0.34,
    rectRadius: 0.12,
    fill: { color: options.fill || C.accent1, transparency: options.transparency || 0 },
    line: { color: options.line || options.fill || C.accent1, transparency: 100 },
    objectName: options.objectName,
  });
  addText(slide, text, x + 0.08, y + 0.01, w - 0.16, (options.h || 0.34) - 0.02, {
    fontSize: options.fontSize || 10,
    color: options.color || C.background1,
    bold: true,
    align: 'center',
    objectName: `${options.objectName || 'pill'}-label`,
  });
}

function addNode(slide, label, x, y, diameter, options = {}) {
  slide.addShape(S.ellipse, {
    x, y, w: diameter, h: diameter,
    fill: { color: options.fill || C.accent1 },
    line: { color: options.line || C.background1, width: options.lineWidth || 1.5 },
    shadow: options.shadow === false ? undefined : freshShadow(0.12, 1.5, 0.7),
    objectName: options.objectName,
  });
  addText(slide, label, x, y, diameter, diameter, {
    fontFace: options.fontFace || 'Cambria',
    fontSize: options.fontSize || 17,
    bold: true,
    align: 'center',
    color: options.color || C.background1,
    objectName: `${options.objectName || 'node'}-label`,
  });
}

function addArrow(slide, x1, y1, x2, y2, color = C.accent1, width = 2) {
  slide.addShape(S.line, {
    x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color, width, endArrowType: 'triangle' },
  });
}

function addStatCard(slide, x, y, w, value, label, accent = C.accent1, sublabel = '') {
  addCard(slide, x, y, w, 1.12, { fill: C.background1, line: C.background2, objectName: `stat-${label}` });
  addNode(slide, '', x + 0.18, y + 0.19, 0.18, { fill: accent, line: accent, shadow: false });
  addText(slide, value, x + 0.48, y + 0.12, w - 0.62, 0.48, {
    fontFace: 'Cambria', fontSize: 25, bold: true, color: C.text1,
  });
  addText(slide, label, x + 0.48, y + 0.58, w - 0.62, 0.25, {
    fontSize: 11.5, bold: true, color: C.text2,
  });
  if (sublabel) {
    addText(slide, sublabel, x + 0.48, y + 0.83, w - 0.62, 0.18, {
      fontSize: 9.5, color: C.text2,
    });
  }
}

function addSource(slide, text, dark = false) {
  addText(slide, text, 0.68, 6.88, 11.65, 0.18, {
    fontSize: 8.5,
    color: dark ? C.background2 : C.text2,
    italic: true,
    objectName: 'source-citation',
  });
}

function addCue(slide, text, dark = false) {
  addPill(slide, 'KEY MESSAGE', 0.70, 0.96, 1.08, {
    h: 0.22,
    fill: dark ? C.accent2 : C.accent1,
    color: C.text1,
    fontSize: 7.3,
    objectName: 'key-message-label',
  });
  addText(slide, text, 1.94, 0.95, 10.18, 0.24, {
    fontSize: 10.2,
    color: dark ? C.background2 : C.text2,
    italic: true,
    objectName: 'key-message-text',
  });
}

function setTitle(slide, title) {
  slide.addText(title, { placeholder: 'title' });
}

function addJointMotif(slide, x, y, scale = 1, dark = false) {
  const c1 = dark ? C.accent2 : C.accent1;
  const c2 = dark ? C.accent1 : C.accent2;
  slide.addShape(S.line, { x: x + 0.18 * scale, y: y + 0.18 * scale, w: 0.70 * scale, h: 0.38 * scale, line: { color: c1, width: 5 * scale } });
  slide.addShape(S.line, { x: x + 0.88 * scale, y: y + 0.56 * scale, w: 0.62 * scale, h: -0.30 * scale, line: { color: c1, width: 5 * scale } });
  addNode(slide, '', x, y, 0.36 * scale, { fill: c2, line: c2, shadow: false });
  addNode(slide, '', x + 0.70 * scale, y + 0.38 * scale, 0.36 * scale, { fill: c2, line: c2, shadow: false });
  addNode(slide, '', x + 1.40 * scale, y + 0.07 * scale, 0.28 * scale, { fill: c1, line: c1, shadow: false });
}

pptx.defineSlideMaster({
  title: 'LIGHT',
  background: { color: THEME.colors.lt1 },
  objects: [
    {
      placeholder: {
        options: {
          name: 'title', type: 'title', x: 0.68, y: 0.37, w: 11.55, h: 0.55,
          fontFace: 'Cambria', fontSize: 30, bold: true, color: C.text1,
          margin: 0, valign: 'mid',
        },
      },
    },
    {
      text: {
        text: 'IIIT-Delhi  •  Robotics Course Project',
        options: { x: 0.68, y: 7.15, w: 4.2, h: 0.16, fontFace: 'Arial', fontSize: 8.5, color: C.text2, margin: 0, isTextBox: true },
      },
    },
    { ellipse: { x: 12.33, y: 0.40, w: 0.16, h: 0.16, fill: { color: C.accent1 }, line: { color: C.accent1 } } },
    { ellipse: { x: 12.58, y: 0.54, w: 0.10, h: 0.10, fill: { color: C.accent2 }, line: { color: C.accent2 } } },
  ],
  slideNumber: { x: 12.25, y: 7.12, w: 0.45, h: 0.20, color: C.text2, fontFace: 'Arial', fontSize: 9, align: 'right', margin: 0 },
  margin: [0.35, 0.65, 0.35, 0.65],
});

pptx.defineSlideMaster({
  title: 'DARK',
  background: { color: THEME.colors.dk1 },
  objects: [
    {
      placeholder: {
        options: {
          name: 'title', type: 'title', x: 0.68, y: 0.37, w: 11.55, h: 0.55,
          fontFace: 'Cambria', fontSize: 30, bold: true, color: C.background1,
          margin: 0, valign: 'mid',
        },
      },
    },
    {
      text: {
        text: 'IIIT-Delhi  •  Robotics Course Project',
        options: { x: 0.68, y: 7.15, w: 4.2, h: 0.16, fontFace: 'Arial', fontSize: 8.5, color: C.background2, margin: 0, isTextBox: true },
      },
    },
    { ellipse: { x: 12.33, y: 0.40, w: 0.16, h: 0.16, fill: { color: C.accent2 }, line: { color: C.accent2 } } },
    { ellipse: { x: 12.58, y: 0.54, w: 0.10, h: 0.10, fill: { color: C.accent1 }, line: { color: C.accent1 } } },
  ],
  slideNumber: { x: 12.25, y: 7.12, w: 0.45, h: 0.20, color: C.background2, fontFace: 'Arial', fontSize: 9, align: 'right', margin: 0 },
  margin: [0.35, 0.65, 0.35, 0.65],
});

// -----------------------------------------------------------------------------
// INTRODUCTION
// -----------------------------------------------------------------------------
pptx.addSection({ title: 'Introduction' });

// Slide 1 — Title
{
  const slide = pptx.addSlide({ masterName: 'DARK', sectionTitle: 'Introduction' });
  addPill(slide, 'PHASE 1 COMPLETE', 0.72, 0.62, 1.86, { fill: C.accent1, fontSize: 10, objectName: 'phase-status' });
  addText(slide, 'Physics-Informed\nInverse Dynamics', 0.72, 1.18, 6.65, 1.52, {
    fontFace: 'Cambria', fontSize: 38, bold: true, color: C.background1, valign: 'top', objectName: 'deck-title',
  });
  addText(slide, 'Data-efficient torque learning and computed-torque tracking for the dm_control two-link reacher', 0.74, 2.88, 5.90, 0.82, {
    fontSize: 18, color: C.background2, valign: 'top', objectName: 'deck-subtitle',
  });
  addCard(slide, 0.74, 3.74, 5.90, 0.56, { fill: C.text2, transparency: 77, line: C.accent2, shadow: false, objectName: 'project-question' });
  addText(slide, 'Project question: can mechanical structure learn accurate torque from less data—and retain that advantage in control?', 0.96, 3.83, 5.46, 0.35, {
    fontSize: 11.5, color: C.background1, bold: true, align: 'center', objectName: 'project-question-text',
  });

  addCard(slide, 7.48, 0.84, 5.10, 4.00, { fill: C.background1, line: C.accent1, shadowOpacity: 0.26, objectName: 'reacher-frame' });
  slide.addImage({ path: REACHER_IMAGE, x: 7.63, y: 0.99, w: 4.80, h: 3.60, objectName: 'reacher-render' });
  addText(slide, 'Authentic dm_control reacher render', 8.05, 4.55, 3.95, 0.20, {
    fontSize: 9.5, color: C.text2, italic: true, align: 'center', objectName: 'render-caption',
  });

  addStatCard(slide, 0.74, 4.58, 1.95, '40,000', 'validated samples', C.accent1);
  addStatCard(slide, 2.88, 4.58, 1.75, '10/10', 'tests passed', C.accent2);
  addStatCard(slide, 4.82, 4.58, 1.75, '0', 'active constraints', C.accent3);
  addText(slide, 'Aayush Gupta  •  Saksham Mishra  •  Shaman Ranjan  •  Aaman Sheikh  •  M Rayhan Khan', 0.76, 6.18, 11.45, 0.30, {
    fontSize: 12.5, color: C.background2, bold: true, objectName: 'team-summary',
  });
  addText(slide, 'Robotics Course Project  •  IIIT-Delhi', 0.76, 6.53, 5.5, 0.25, {
    fontSize: 11, color: C.accent2, objectName: 'course-label',
  });
  addJointMotif(slide, 11.35, 5.72, 0.72, true);
  slide.addNotes('Opening script:\nOur project learns the joint torques required for a desired robot-arm movement. We compare a physics-informed Lagrangian model with a normal neural network and MuJoCo analytical dynamics. Phase 1—the verified physics and data foundation—is complete; the neural models and controller belong to the upcoming phases. The three numbers at the bottom summarize our current evidence: 40,000 validated rows, all 10 tests passing, and zero active constraints.');
}

// Slide 2 — Problem and motivation
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Introduction' });
  setTitle(slide, 'From desired motion to joint torque');
  addCue(slide, 'We learn the map from desired joint motion to torque, then test whether it remains useful inside feedback control.');

  const y = 1.45;
  addNode(slide, 'q', 0.85, y, 0.68, { fill: C.accent6, objectName: 'q-node' });
  addNode(slide, 'q̇', 1.70, y, 0.68, { fill: C.accent6, objectName: 'qd-node' });
  addNode(slide, 'q̈', 2.55, y, 0.68, { fill: C.accent6, objectName: 'qdd-node' });
  addArrow(slide, 3.42, y + 0.34, 4.28, y + 0.34, C.accent1, 2.5);
  addCard(slide, 4.42, 1.18, 3.40, 1.28, { fill: C.background2, line: C.accent1, objectName: 'inverse-dynamics-block' });
  addText(slide, 'INVERSE DYNAMICS', 4.70, 1.35, 2.84, 0.36, { fontFace: 'Cambria', fontSize: 21, bold: true, align: 'center' });
  addText(slide, 'Learned or analytical model', 4.70, 1.78, 2.84, 0.24, { fontSize: 11.5, color: C.text2, align: 'center' });
  addArrow(slide, 7.98, y + 0.34, 8.90, y + 0.34, C.accent1, 2.5);
  addNode(slide, 'τ', 9.08, y, 0.68, { fill: C.accent2, objectName: 'tau-node' });
  addArrow(slide, 9.95, y + 0.34, 10.80, y + 0.34, C.accent2, 2.5);
  addJointMotif(slide, 11.00, 1.32, 0.78, false);

  addRichText(slide, [
    { text: 'Input: ', options: { bold: true, color: C.text1 } },
    { text: 'joint angles, velocities, and desired accelerations', options: { color: C.text2 } },
  ], 0.88, 2.72, 5.75, 0.34, { fontSize: 14 });
  addRichText(slide, [
    { text: 'Output: ', options: { bold: true, color: C.text1 } },
    { text: 'generalized shoulder and wrist torques in N·m', options: { color: C.text2 } },
  ], 6.84, 2.72, 5.62, 0.34, { fontSize: 14 });

  const useCases = [
    ['Precision assembly', 'Lower tracking error during fast repeated motions', C.accent1],
    ['Changing payloads', 'Learn dynamics without measuring every physical parameter', C.accent2],
    ['Collaborative robots', 'Accurate feedforward torque with lower feedback stiffness', C.accent3],
  ];
  useCases.forEach((item, i) => {
    const x = 0.82 + i * 4.12;
    addCard(slide, x, 3.48, 3.72, 2.22, { fill: C.background1, line: item[2], objectName: `use-case-${i}` });
    addNode(slide, `${i + 1}`, x + 0.23, 3.76, 0.50, { fill: item[2], line: item[2], fontSize: 15, shadow: false });
    addText(slide, item[0], x + 0.88, 3.70, 2.50, 0.42, { fontFace: 'Cambria', fontSize: 18, bold: true });
    addText(slide, item[1], x + 0.28, 4.40, 3.10, 0.78, { fontSize: 13, color: C.text2, valign: 'top' });
  });
  addSource(slide, 'Concept basis: robot inverse dynamics and computed-torque control literature');
  slide.addNotes('Speaking script:\nInverse dynamics converts desired motion into required force or torque. Our six inputs are two angles, two velocities, and two desired accelerations; our outputs are two joint torques. This is supervised dynamics learning, not reinforcement learning. The same capability supports precision assembly, payload adaptation, and compliant collaborative robots.');
}

// Slide 3 — Plant
{
  const slide = pptx.addSlide({ masterName: 'DARK', sectionTitle: 'Introduction' });
  setTitle(slide, 'The plant: a two-joint horizontal reacher');
  addCue(slide, 'The built-in reacher supplies the plant; our project replaces point-reaching with joint-space trajectory tracking.', true);
  addCard(slide, 0.72, 1.18, 5.70, 4.40, { fill: C.background1, line: C.accent1, shadowOpacity: 0.25, objectName: 'plant-image-frame' });
  slide.addImage({ path: REACHER_IMAGE, x: 0.90, y: 1.37, w: 5.34, h: 4.01, objectName: 'plant-image' });

  const specs = [
    ['2 DoF', 'shoulder + wrist'],
    ['50 Hz', 'physics and control'],
    ['±160°', 'wrist limit'],
    ['0.01', 'joint damping'],
    ['±0.05 N·m', 'torque per joint'],
    ['No contact', 'primary regime'],
  ];
  specs.forEach((s, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 6.82 + col * 2.82;
    const y = 1.18 + row * 1.28;
    addCard(slide, x, y, 2.52, 1.02, { fill: C.text2, transparency: 72, line: col === 0 ? C.accent1 : C.accent2, shadow: false, objectName: `spec-${i}` });
    addText(slide, s[0], x + 0.18, y + 0.12, 2.15, 0.40, { fontFace: 'Cambria', fontSize: 20, bold: true, color: C.background1, align: 'center' });
    addText(slide, s[1], x + 0.18, y + 0.57, 2.15, 0.22, { fontSize: 10.5, color: C.background2, align: 'center' });
  });

  addCard(slide, 6.82, 5.05, 5.34, 1.02, { fill: C.accent2, line: C.accent2, shadow: false, objectName: 'torque-insight' });
  addText(slide, 'Critical implementation fact', 7.10, 5.18, 2.18, 0.26, { fontSize: 11, bold: true, color: C.text1 });
  addText(slide, 'τjoint = 0.05 × ctrl', 9.24, 5.10, 2.55, 0.40, { fontFace: 'Cambria', fontSize: 22, bold: true, color: C.text1, align: 'center' });
  addText(slide, 'The built-in target is visual/task context—not a causal dynamics input.', 7.10, 5.52, 4.70, 0.26, { fontSize: 11.5, color: C.text1 });
  addSource(slide, 'Sources: dm_control 1.0.52 reacher.py and reacher.xml; MuJoCo 4.0.1 computation docs', true);
  slide.addNotes('Speaking script:\nThe plant is DeepMind Control Suite’s two-link horizontal reacher. It runs at 50 Hz, includes viscous damping, and limits wrist rotation to plus or minus 160 degrees. The action called ctrl is not torque: the motor gear multiplies it by 0.05. We reuse this plant but replace the stock point-reaching objective with a custom joint-space tracking experiment.');
}

// Slide 4 — Model comparison
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Introduction' });
  setTitle(slide, 'A controlled comparison—not just another neural network');
  addCue(slide, 'All learned models see identical trajectories and budgets; the physics prior is the controlled experimental difference.');
  const models = [
    {
      x: 0.72, name: 'MuJoCo analytical', tag: 'GROUND TRUTH', color: C.accent6,
      headline: 'Exact simulator dynamics',
      lines: ['mj_inverse torque oracle', 'Correctness ceiling', 'Controller benchmark'],
    },
    {
      x: 4.78, name: 'Lagrangian / DeLaN', tag: 'PHYSICS-INFORMED', color: C.accent1,
      headline: 'Learns structured mechanics',
      lines: ['Positive-definite M(q)', 'Euler–Lagrange torque', 'Explicit viscous damping'],
    },
    {
      x: 8.84, name: 'Black-box MLP', tag: 'DATA-DRIVEN', color: C.accent2,
      headline: 'Learns the map directly',
      lines: ['Same records and budgets', 'Matched model scale', 'No mechanics equation'],
    },
  ];
  models.forEach((m, i) => {
    addCard(slide, m.x, 1.25, 3.72, 4.82, { fill: C.background1, line: m.color, objectName: `model-card-${i}` });
    addPill(slide, m.tag, m.x + 0.27, 1.53, 1.65, { fill: m.color, fontSize: 8.5, objectName: `model-tag-${i}` });
    addNode(slide, `${i + 1}`, m.x + 2.78, 1.45, 0.58, { fill: m.color, line: m.color, fontSize: 15, shadow: false });
    addText(slide, m.name, m.x + 0.28, 2.24, 3.10, 0.58, { fontFace: 'Cambria', fontSize: 21, bold: true, color: C.text1, valign: 'top' });
    addText(slide, m.headline, m.x + 0.28, 2.96, 3.05, 0.34, { fontSize: 12.5, bold: true, color: m.color });
    m.lines.forEach((line, idx) => {
      addNode(slide, '', m.x + 0.31, 3.58 + idx * 0.59, 0.14, { fill: m.color, line: m.color, shadow: false });
      addText(slide, line, m.x + 0.58, 3.47 + idx * 0.59, 2.70, 0.34, { fontSize: 13, color: C.text2 });
    });
    addText(slide, '(q, q̇, q̈)  →  τ', m.x + 0.48, 5.40, 2.76, 0.36, { fontFace: 'Cambria', fontSize: 18, bold: true, align: 'center', color: C.text1 });
  });
  addPill(slide, 'FAIRNESS: SAME TRAJECTORIES • SAME 10/30/100% BUDGETS • SAME CONTROLLER', 2.66, 6.31, 7.98, { fill: C.text1, color: C.background1, fontSize: 10 });
  addSource(slide, 'Method basis: DeLaN, LNN, structured mechanical models, and MuJoCo inverse dynamics');
  slide.addNotes('Speaking script:\nWe compare three viewpoints on the same torque function. MuJoCo is the exact simulator oracle, DeLaN learns a mechanically structured model, and the MLP learns the map directly. Both learned models receive the same trajectories, budgets, preprocessing, and later the same controller trials. This makes the physics prior—not a hidden data advantage—the main experimental difference.');
}

// -----------------------------------------------------------------------------
// PHASE 1 PROGRESS
// -----------------------------------------------------------------------------
pptx.addSection({ title: 'Phase 1: Completed Foundation' });

// Slide 5 — Roadmap
{
  const slide = pptx.addSlide({ masterName: 'DARK', sectionTitle: 'Phase 1: Completed Foundation' });
  setTitle(slide, 'Three implementation phases • current position');
  addCue(slide, 'Phase 1 is finished; model learning and closed-loop evaluation are the two remaining implementation stages.', true);
  const phaseData = [
    { x: 0.78, n: '1', title: 'Physics & data', status: 'COMPLETE', color: C.accent1, body: ['Pinned simulator', 'Analytical dynamics', '40k validated samples'] },
    { x: 4.68, n: '2', title: 'Models & learning', status: 'UPCOMING', color: C.accent2, body: ['DeLaN + damping', 'BB-ID and BB-FD', '10/30/100% training'] },
    { x: 8.58, n: '3', title: 'Control & demo', status: 'UPCOMING', color: C.accent3, body: ['Computed torque', '10 ID + 10 OOD trials', 'Live demo + final report'] },
  ];
  addArrow(slide, 3.78, 3.25, 4.42, 3.25, C.background2, 2.5);
  addArrow(slide, 7.68, 3.25, 8.32, 3.25, C.background2, 2.5);
  phaseData.forEach((p, i) => {
    addCard(slide, p.x, 1.43, 3.18, 4.05, { fill: C.text2, transparency: i === 0 ? 62 : 78, line: p.color, shadowOpacity: 0.23, objectName: `phase-card-${i}` });
    addNode(slide, p.n, p.x + 1.20, 1.10, 0.78, { fill: p.color, line: p.color, fontSize: 23, objectName: `phase-node-${i}` });
    addPill(slide, p.status, p.x + 0.72, 2.17, 1.74, { fill: p.color, color: C.text1, fontSize: 9, objectName: `phase-status-${i}` });
    addText(slide, p.title, p.x + 0.28, 2.78, 2.62, 0.52, { fontFace: 'Cambria', fontSize: 21, bold: true, color: C.background1, align: 'center' });
    p.body.forEach((line, idx) => {
      addNode(slide, '', p.x + 0.42, 3.58 + idx * 0.52, 0.13, { fill: p.color, line: p.color, shadow: false });
      addText(slide, line, p.x + 0.68, 3.45 + idx * 0.52, 2.04, 0.32, { fontSize: 12.5, color: C.background2 });
    });
  });
  addPill(slide, 'CURRENT GATE: verified labels, splits, units, constraints, and reproducibility', 2.70, 6.12, 7.92, { fill: C.accent1, color: C.text1, fontSize: 11 });
  slide.addNotes('Speaking script:\nWe divided implementation into three gated phases. Phase 1 establishes correct physics and data and is complete. Phase 2 implements and trains all dynamics models, while Phase 3 places the inverse models inside computed-torque control. We do not proceed to training unless the Phase 1 units, constraints, labels, and splits all pass validation.');
}

// Slide 6 — Phase 1 methodology
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Phase 1: Completed Foundation' });
  setTitle(slide, 'Phase 1 methodology: two independent paths must agree');
  addCue(slide, 'A sample enters training only after native MuJoCo and an independent analytical implementation agree.');
  const steps = [
    ['1', 'Pin runtime', 'Python, packages, XML hash'],
    ['2', 'Inspect plant', 'DoF, gears, limits, timestep'],
    ['3', 'Derive physics', 'M(q), c(q,q̇), damping'],
    ['4', 'Generate motion', 'Exact q, q̇, q̈ multi-sines'],
    ['5', 'Label in MuJoCo', 'mj_inverse → τjoint'],
    ['6', 'Audit & serialize', 'splits, budgets, hashes, tests'],
  ];
  steps.forEach((step, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.76 + col * 4.15;
    const y = 1.36 + row * 2.42;
    addCard(slide, x, y, 3.62, 1.82, { fill: row === 0 ? C.background1 : C.background2, line: i % 2 === 0 ? C.accent1 : C.accent2, objectName: `method-step-${i}` });
    addNode(slide, step[0], x + 0.22, y + 0.26, 0.55, { fill: i % 2 === 0 ? C.accent1 : C.accent2, line: i % 2 === 0 ? C.accent1 : C.accent2, fontSize: 15, shadow: false });
    addText(slide, step[1], x + 0.95, y + 0.22, 2.28, 0.42, { fontFace: 'Cambria', fontSize: 18, bold: true });
    addText(slide, step[2], x + 0.95, y + 0.74, 2.30, 0.54, { fontSize: 12.5, color: C.text2, valign: 'top' });
  });
  addArrow(slide, 4.38, 2.27, 4.78, 2.27, C.accent6, 2);
  addArrow(slide, 8.53, 2.27, 8.93, 2.27, C.accent6, 2);
  addArrow(slide, 4.38, 4.69, 4.78, 4.69, C.accent6, 2);
  addArrow(slide, 8.53, 4.69, 8.93, 4.69, C.accent6, 2);

  addCard(slide, 2.06, 6.08, 9.20, 0.56, { fill: C.text1, line: C.text1, shadow: false, objectName: 'two-path-proof' });
  addText(slide, 'Independent closed form  ⇄  native MuJoCo  →  disagreement near floating-point precision', 2.28, 6.19, 8.74, 0.28, { fontSize: 13, bold: true, color: C.background1, align: 'center' });
  addSource(slide, 'Implemented in src/reacher_id/{environment,dynamics,trajectories,dataset,validation}.py');
  slide.addNotes('Speaking script:\nFirst we pin and inspect the exact simulator. Second, we derive the two-link equations independently. Third, we generate smooth trajectories with exact analytical derivatives and ask MuJoCo inverse dynamics for torque. Finally, we audit every field, build trajectory-level splits, and serialize hashes and manifests. The scientific safeguard is that MuJoCo and the independently written equations must agree before data are accepted.');
}

// Slide 7 — Dynamics equations
{
  const slide = pptx.addSlide({ masterName: 'DARK', sectionTitle: 'Phase 1: Completed Foundation' });
  setTitle(slide, 'Dynamics and torque semantics we verified');
  addCue(slide, 'Correct force spaces and damping signs are essential—otherwise low training loss would describe the wrong physics.', true);
  addCard(slide, 0.76, 1.26, 6.20, 4.86, { fill: C.text2, transparency: 68, line: C.accent1, shadow: false, objectName: 'equation-panel' });
  addText(slide, 'Smooth inverse dynamics', 1.10, 1.58, 2.75, 0.35, { fontFace: 'Cambria', fontSize: 18, bold: true, color: C.accent1 });
  addText(slide, 'τ = M(q)q̈ + c(q,q̇) + 0.01q̇', 1.10, 2.02, 5.46, 0.64, { fontFace: 'Cambria', fontSize: 26, bold: true, color: C.background1, align: 'center' });
  addText(slide, 'Mass matrix', 1.10, 2.92, 2.10, 0.32, { fontFace: 'Cambria', fontSize: 17, bold: true, color: C.accent2 });
  addText(slide, 'M(q) =  [ A + 2B cos(q₂)     D + B cos(q₂) ]\n             [ D + B cos(q₂)          D          ]', 1.10, 3.32, 5.46, 1.10, { fontFace: 'Cambria', fontSize: 18, color: C.background1, align: 'center', valign: 'top' });
  addText(slide, 'Actuator transmission', 1.10, 4.78, 2.45, 0.32, { fontFace: 'Cambria', fontSize: 17, bold: true, color: C.accent2 });
  addText(slide, 'τjoint = 0.05 × ctrl', 1.10, 5.16, 5.46, 0.52, { fontFace: 'Cambria', fontSize: 23, bold: true, color: C.background1, align: 'center' });

  const facts = [
    ['Gravity exists—but projects to zero torque', 'Horizontal links rotate around vertical axes; COM height is constant.', C.accent1],
    ['Damping is non-conservative', 'Passive force is −0.01q̇, so required motor torque adds +0.01q̇.', C.accent2],
    ['Joint limits create a different regime', 'Primary rows require qfrc_constraint = 0 and nefc = 0.', C.accent3],
  ];
  facts.forEach((f, i) => {
    const y = 1.34 + i * 1.60;
    addCard(slide, 7.36, y, 5.18, 1.27, { fill: C.text2, transparency: 76, line: f[2], shadow: false, objectName: `physics-fact-${i}` });
    addNode(slide, `${i + 1}`, 7.62, y + 0.29, 0.53, { fill: f[2], line: f[2], fontSize: 14, shadow: false });
    addText(slide, f[0], 8.36, y + 0.18, 3.74, 0.36, { fontFace: 'Cambria', fontSize: 16, bold: true, color: C.background1 });
    addText(slide, f[1], 8.36, y + 0.62, 3.76, 0.44, { fontSize: 11.5, color: C.background2, valign: 'top' });
  });
  addSource(slide, 'Sources: MuJoCo 4.0.1 equations/fields; independent two-link derivation cross-checked at 512 random states', true);
  slide.addNotes('Speaking script:\nThe required torque contains inertia, Coriolis and centrifugal bias, and a positive damping-compensation term. MuJoCo passive damping is negative 0.01 times velocity, so the motor must add positive 0.01 times velocity to overcome it. Gravity is enabled, but horizontal motion keeps every center of mass at constant height, so generalized gravity torque is zero. We also keep every training row away from active joint limits.');
}

// Slide 8 — Dataset composition
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Phase 1: Completed Foundation' });
  setTitle(slide, 'Dataset design: trajectories and distribution shifts');
  addCue(slide, 'Trajectory-level splits prevent leakage; two OOD sets separate symmetry generalization from true inertia extrapolation.');
  slide.addChart(CH.doughnut, [
    {
      name: 'Samples',
      labels: ['Training', 'Validation', 'ID test', 'OOD test'],
      values: [25000, 5000, 5000, 5000],
    },
  ], {
    x: 0.65, y: 1.25, w: 4.65, h: 4.18,
    holeSize: 62,
    showLegend: true,
    legendPos: 'b',
    legendFontFace: '+mn-lt',
    legendFontSize: 10,
    legendColor: THEME.colors.dk2,
    showPercent: true,
    showCategoryName: false,
    showValue: false,
    dataLabelPosition: 'bestFit',
    dataLabelColor: THEME.colors.dk1,
    dataLabelFormatCode: '0%',
    chartColors: [THEME.colors.accent1, THEME.colors.accent2, THEME.colors.accent6, THEME.colors.accent3],
    border: { color: THEME.colors.lt1, pt: 0 },
    showTitle: true,
    title: '40,000 synchronized samples',
    titleFontFace: '+mj-lt',
    titleFontSize: 15,
    titleColor: THEME.colors.dk1,
  });

  addStatCard(slide, 5.63, 1.27, 2.03, '160', 'trajectories', C.accent1, '250 samples each');
  addStatCard(slide, 7.86, 1.27, 2.03, '5 s', 'per trajectory', C.accent2, 'sampled at 50 Hz');
  addStatCard(slide, 10.09, 1.27, 2.03, '3', 'nested budgets', C.accent6, '10% • 30% • 100%');

  addCard(slide, 5.63, 2.70, 3.12, 2.08, { fill: C.background2, line: C.accent1, objectName: 'shoulder-ood-card' });
  addNode(slide, 'q₁', 5.89, 2.97, 0.58, { fill: C.accent1, line: C.accent1, shadow: false });
  addText(slide, 'Shoulder OOD', 6.68, 2.93, 1.76, 0.38, { fontFace: 'Cambria', fontSize: 17, bold: true });
  addText(slide, 'Absolute angle outside training range; true dynamics should remain invariant.', 5.90, 3.61, 2.55, 0.74, { fontSize: 12.2, color: C.text2, valign: 'top' });

  addCard(slide, 8.99, 2.70, 3.12, 2.08, { fill: C.background2, line: C.accent3, objectName: 'wrist-ood-card' });
  addNode(slide, 'q₂', 9.25, 2.97, 0.58, { fill: C.accent3, line: C.accent3, shadow: false });
  addText(slide, 'Wrist OOD', 10.04, 2.93, 1.74, 0.38, { fontFace: 'Cambria', fontSize: 17, bold: true });
  addText(slide, 'Unseen relative configuration; inertia and Coriolis terms genuinely change.', 9.26, 3.61, 2.54, 0.74, { fontSize: 12.2, color: C.text2, valign: 'top' });

  addCard(slide, 5.63, 5.16, 6.48, 1.02, { fill: C.text1, line: C.text1, shadow: false, objectName: 'leakage-callout' });
  addText(slide, 'No row-level random split', 5.92, 5.30, 2.30, 0.26, { fontSize: 12, bold: true, color: C.accent2 });
  addText(slide, 'Adjacent time samples stay together under one trajectory ID.', 8.24, 5.28, 3.52, 0.30, { fontSize: 12, color: C.background1 });
  addText(slide, 'Each budget fits its own training-only normalizer—no hidden information from larger budgets.', 5.92, 5.69, 5.84, 0.26, { fontSize: 11.2, color: C.background2 });
  addSource(slide, 'Artifacts: data/processed/{split,budget,trajectory}_manifest.json and normalization_{10,30,100}.json');
  slide.addNotes('Speaking script:\nThe dataset contains 160 complete five-second trajectories and 40,000 rows. We split complete trajectories because adjacent samples are highly correlated; random row splitting would leak near-duplicates. Shoulder OOD tests rotational symmetry, whereas wrist OOD changes the true inertia and Coriolis terms. Each 10, 30, and 100 percent budget also fits its own normalizer using only its training rows.');
}

// Slide 9 — Validation evidence
{
  const slide = pptx.addSlide({ masterName: 'DARK', sectionTitle: 'Phase 1: Completed Foundation' });
  setTitle(slide, 'Phase 1 evidence: every acceptance gate passes');
  addCue(slide, 'The complete dataset is constraint-free and agrees with analytical mechanics to roughly 17–18 decimal orders.', true);
  const statX = [0.72, 3.78, 6.84, 9.90];
  const statData = [
    ['40,000', 'feasible rows', C.accent1],
    ['0', 'active constraints', C.accent3],
    ['10/10', 'automated tests', C.accent2],
    ['0', 'native relabel error', C.accent5],
  ];
  statData.forEach((s, i) => {
    addCard(slide, statX[i], 1.18, 2.70, 1.12, { fill: C.text2, transparency: 72, line: s[2], shadow: false, objectName: `validation-stat-${i}` });
    addText(slide, s[0], statX[i] + 0.16, 1.28, 2.38, 0.42, { fontFace: 'Cambria', fontSize: 25, bold: true, color: C.background1, align: 'center' });
    addText(slide, s[1], statX[i] + 0.16, 1.77, 2.38, 0.23, { fontSize: 10.5, bold: true, color: C.background2, align: 'center' });
  });

  slide.addChart(CH.bar, [
    {
      name: 'Agreement digits',
      labels: ['Mass matrix', 'Bias force', 'Inverse torque', 'Stored labels'],
      values: [18.06, 17.66, 17.16, 17.06],
    },
  ], {
    x: 0.78, y: 2.73, w: 6.80, h: 3.55,
    catAxisLabelFontFace: '+mn-lt',
    catAxisLabelFontSize: 10,
    catAxisLabelColor: THEME.colors.lt2,
    valAxisLabelFontFace: '+mn-lt',
    valAxisLabelFontSize: 9,
    valAxisLabelColor: THEME.colors.lt2,
    valAxisMinVal: 0,
    valAxisMaxVal: 20,
    valAxisMajorUnit: 5,
    valGridLine: { color: THEME.colors.dk2, size: 1 },
    catGridLine: { style: 'none' },
    chartColors: [THEME.colors.accent1],
    invertedColors: [THEME.colors.accent1],
    showLegend: false,
    showTitle: true,
    title: 'Agreement with independent analytical model\n(−log₁₀ maximum absolute error)',
    titleFontFace: '+mj-lt',
    titleFontSize: 14,
    titleColor: THEME.colors.lt1,
    showValue: true,
    dataLabelPosition: 'outEnd',
    dataLabelColor: THEME.colors.lt1,
    dataLabelFormatCode: '0.0',
    showCatName: false,
    showValAxisTitle: false,
    showCatAxisTitle: false,
    showBorder: false,
    showValue: true,
    barDir: 'bar',
  });

  addCard(slide, 7.91, 2.73, 4.62, 3.55, { fill: C.text2, transparency: 72, line: C.accent2, shadow: false, objectName: 'validation-proof-card' });
  addText(slide, 'What this proves', 8.22, 3.02, 3.96, 0.42, { fontFace: 'Cambria', fontSize: 21, bold: true, color: C.background1 });
  const proofs = [
    'Correct joint order, signs, and units',
    'No stale or aliased MuJoCo arrays',
    'Exact q / q̇ / q̈ temporal alignment',
    'Disjoint splits and nested budgets',
    'Positive-definite mass matrix',
  ];
  proofs.forEach((p, i) => {
    addNode(slide, '✓', 8.26, 3.68 + i * 0.47, 0.27, { fill: i % 2 ? C.accent2 : C.accent1, line: i % 2 ? C.accent2 : C.accent1, fontSize: 10, shadow: false });
    addText(slide, p, 8.72, 3.61 + i * 0.47, 3.26, 0.30, { fontSize: 12.2, color: C.background2 });
  });
  addSource(slide, 'Evidence: artifacts/phase1_validation.json • dataset SHA-256 f0cdd9a2…e78299', true);
  slide.addNotes('Speaking script:\nEvery acceptance gate passes. The bars show negative log base ten of maximum error, so values near 17 or 18 mean agreement at approximately machine precision. All 40,000 rows are feasible, no row activates a constraint, and native MuJoCo relabeling reproduces the stored torques exactly. This proves the future learning comparison starts from trustworthy labels.');
}

// Slide 10 — Reproducibility
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Phase 1: Completed Foundation' });
  setTitle(slide, 'Reproducibility is an implemented feature');
  addCue(slide, 'Locks, hashes, seeds, and manifests allow another evaluator to recreate the same plant and numerical dataset.');
  const layers = [
    ['1', 'Locked software', 'Python 3.12 • uv.lock • exact package versions', C.accent6],
    ['2', 'Locked plant', 'XML SHA-256 • dimensions • gears • timesteps', C.accent1],
    ['3', 'Locked data process', 'Seeds • trajectory coefficients • split IDs • budgets', C.accent2],
    ['4', 'Locked evidence', 'Dataset content hash • validation JSON • tests', C.accent3],
  ];
  layers.forEach((l, i) => {
    const x = 0.86 + i * 3.08;
    addCard(slide, x, 1.32, 2.72, 3.42, { fill: i % 2 === 0 ? C.background1 : C.background2, line: l[3], objectName: `repro-layer-${i}` });
    addNode(slide, l[0], x + 0.92, 1.04, 0.72, { fill: l[3], line: l[3], fontSize: 20, objectName: `repro-node-${i}` });
    addText(slide, l[1], x + 0.25, 2.04, 2.22, 0.50, { fontFace: 'Cambria', fontSize: 18, bold: true, align: 'center' });
    addText(slide, l[2], x + 0.32, 2.86, 2.08, 1.02, { fontSize: 12.5, color: C.text2, align: 'center', valign: 'top' });
  });

  addCard(slide, 0.88, 5.25, 7.55, 1.12, { fill: C.text1, line: C.text1, shadow: false, objectName: 'repro-command' });
  addText(slide, '$ uv sync --frozen --extra dev\n$ reacher-phase1 all --force    &&    pytest', 1.16, 5.45, 7.02, 0.68, { fontFace: 'Courier New', fontSize: 14, bold: true, color: C.background1, valign: 'top' });
  addCard(slide, 8.75, 5.25, 3.68, 1.12, { fill: C.background2, line: C.accent2, shadow: false, objectName: 'compatibility-decision' });
  addText(slide, 'Compatibility decision', 9.03, 5.40, 3.08, 0.28, { fontSize: 11, bold: true, color: C.accent3 });
  addText(slide, 'Python 3.12 selected after Python 3.14 exposed a missing labmaze wheel.', 9.03, 5.75, 3.08, 0.43, { fontSize: 11, color: C.text2, valign: 'top' });
  addSource(slide, 'Reproduction guide: docs/phase1_implementation.md • viva guide: docs/phase1_viva_handbook.md');
  slide.addNotes('Speaking script:\nReproducibility means more than listing package versions. We lock Python and dependencies, hash the exact robot XML, record every seed and trajectory coefficient, and hash the dataset content. Python 3.14 was tested but rejected because the required labmaze wheel was missing; Python 3.12 gives a complete reproducible stack. The two commands shown recreate and validate the phase.');
}

// -----------------------------------------------------------------------------
// NEXT PHASES
// -----------------------------------------------------------------------------
pptx.addSection({ title: 'Upcoming Phases' });

// Slide 11 — Phase 2
{
  const slide = pptx.addSlide({ masterName: 'DARK', sectionTitle: 'Upcoming Phases' });
  setTitle(slide, 'Upcoming Phase 2: learn, compare, and stress-test dynamics');
  addCue(slide, 'Phase 2 asks whether Lagrangian structure reduces the data needed for accurate prediction and rollout.', true);
  const models = [
    ['DeLaN + damping', 'Mθ(q), Vθ(q), Bθ\nEuler–Lagrange torque', C.accent1],
    ['BB-ID', '(q, q̇, q̈) → τ\nDirect inverse MLP', C.accent2],
    ['BB-FD', '(q, q̇, τ) → q̈\nForward rollout MLP', C.accent3],
  ];
  models.forEach((m, i) => {
    const x = 0.80 + i * 4.10;
    addCard(slide, x, 1.34, 3.62, 2.05, { fill: C.text2, transparency: 72, line: m[2], shadow: false, objectName: `phase2-model-${i}` });
    addNode(slide, `${i + 1}`, x + 0.24, 1.62, 0.56, { fill: m[2], line: m[2], fontSize: 15, shadow: false });
    addText(slide, m[0], x + 0.98, 1.52, 2.24, 0.42, { fontFace: 'Cambria', fontSize: 19, bold: true, color: C.background1 });
    addText(slide, m[1], x + 0.40, 2.26, 2.78, 0.62, { fontSize: 13, color: C.background2, align: 'center', valign: 'top' });
  });

  addArrow(slide, 2.60, 3.82, 2.60, 4.40, C.accent1, 2.2);
  addArrow(slide, 6.70, 3.82, 6.70, 4.40, C.accent2, 2.2);
  addArrow(slide, 10.80, 3.82, 10.80, 4.40, C.accent3, 2.2);
  addCard(slide, 0.82, 4.50, 11.68, 1.55, { fill: C.text2, transparency: 78, line: C.background2, shadow: false, objectName: 'phase2-experiment-band' });
  addPill(slide, 'TRAIN', 1.13, 4.84, 1.00, { fill: C.accent1, color: C.text1, fontSize: 9 });
  addText(slide, '10%  •  30%  •  100% of complete trajectories', 2.36, 4.80, 3.54, 0.31, { fontSize: 13.5, bold: true, color: C.background1 });
  addPill(slide, 'REPEAT', 6.07, 4.84, 1.08, { fill: C.accent2, color: C.text1, fontSize: 9 });
  addText(slide, '5 initialization / subset seeds', 7.37, 4.80, 2.26, 0.31, { fontSize: 13.5, bold: true, color: C.background1 });
  addPill(slide, 'EVALUATE', 9.80, 4.84, 1.25, { fill: C.accent3, color: C.text1, fontSize: 9 });
  addText(slide, 'ID + two OOD regimes', 11.16, 4.80, 1.06, 0.31, { fontSize: 11.5, bold: true, color: C.background1 });
  addText(slide, 'Outputs: torque RMSE • learning curves • mass-matrix diagnostics • 2-second rollout error • failure rates', 1.17, 5.46, 10.86, 0.30, { fontSize: 12.3, color: C.background2, align: 'center' });
  addSource(slide, 'Phase 2 gate: all budgets and seeds evaluated without using validation/test rows for fitting', true);
  slide.addNotes('Speaking script:\nPhase 2 implements three learned components. DeLaN learns inertia, potential, and damping and derives both inverse and forward dynamics. BB-ID predicts torque and will be used in computed-torque control; BB-FD separately predicts acceleration for a fair open-loop rollout baseline. Every architecture is trained at 10, 30, and 100 percent data across repeated seeds and evaluated on ID plus two OOD regimes.');
}

// Slide 12 — Phase 3
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Upcoming Phases' });
  setTitle(slide, 'Upcoming Phase 3: close the loop and demonstrate tracking');
  addCue(slide, 'Phase 3 tests the practical outcome: reliable tracking under identical gains, references, and torque limits.');

  // Closed-loop diagram
  const boxes = [
    { x: 0.66, w: 2.05, title: 'Reference', sub: 'qᵈ, q̇ᵈ, q̈ᵈ', color: C.accent6 },
    { x: 3.15, w: 2.25, title: 'Acceleration law', sub: 'q̈cmd = q̈ᵈ + Kdė + Kpe', color: C.accent1 },
    { x: 5.86, w: 2.10, title: 'Inverse model', sub: '(q, q̇, q̈cmd) → τ', color: C.accent2 },
    { x: 8.42, w: 1.90, title: 'Torque limit', sub: 'ctrl = clip(τ/0.05)', color: C.accent3 },
    { x: 10.78, w: 1.88, title: 'MuJoCo arm', sub: 'q, q̇ feedback', color: C.accent5 },
  ];
  boxes.forEach((b, i) => {
    addCard(slide, b.x, 1.38, b.w, 1.34, { fill: i % 2 ? C.background2 : C.background1, line: b.color, objectName: `control-block-${i}` });
    addNode(slide, `${i + 1}`, b.x + 0.14, 1.55, 0.39, { fill: b.color, line: b.color, fontSize: 11, shadow: false });
    addText(slide, b.title, b.x + 0.61, 1.50, b.w - 0.77, 0.31, { fontFace: 'Cambria', fontSize: 15, bold: true });
    addText(slide, b.sub, b.x + 0.22, 2.04, b.w - 0.44, 0.34, { fontSize: 10.5, color: C.text2, align: 'center' });
    if (i < boxes.length - 1) addArrow(slide, b.x + b.w + 0.08, 2.04, boxes[i + 1].x - 0.10, 2.04, b.color, 1.8);
  });
  // Feedback path
  slide.addShape(S.line, { x: 11.72, y: 2.84, w: 0, h: 0.48, line: { color: C.accent5, width: 2 } });
  slide.addShape(S.line, { x: 11.72, y: 3.32, w: -7.42, h: 0, line: { color: C.accent5, width: 2, endArrowType: 'triangle' } });
  addPill(slide, 'FEEDBACK', 7.41, 3.12, 1.14, { fill: C.accent5, color: C.text1, fontSize: 8.5, h: 0.31 });

  const metrics = [
    ['10 + 10', 'ID and OOD trials', C.accent1],
    ['RMSE', 'joint + fingertip', C.accent2],
    ['SUCCESS', 'fixed criterion / 10', C.accent3],
    ['SATURATION', 'torque and limit events', C.accent6],
  ];
  metrics.forEach((m, i) => addStatCard(slide, 0.76 + i * 3.05, 4.12, 2.72, m[0], m[1], m[2]));

  addCard(slide, 0.78, 5.60, 11.73, 0.77, { fill: C.text1, line: C.text1, shadow: false, objectName: 'phase3-demo-output' });
  addText(slide, 'Final evaluator experience', 1.04, 5.75, 2.05, 0.27, { fontSize: 11, bold: true, color: C.accent2 });
  addText(slide, 'Switchable analytical / DeLaN / MLP controllers  •  live tracking and torque display  •  saved fallback videos', 3.08, 5.72, 8.96, 0.32, { fontSize: 12.5, color: C.background1, align: 'center' });
  addSource(slide, 'Controller gains selected once with the analytical validation controller, then frozen for every model');
  slide.addNotes('Speaking script:\nPhase 3 converts tracking error into a corrected acceleration command. The selected inverse model maps the current measured state and corrected acceleration to torque, which is clipped to the physical actuator range before entering MuJoCo. Gains are selected once with the analytical validation controller and then frozen. Each model receives the same ten ID and ten OOD references, initial states, gains, and limits.');
}

// Slide 13 — Final evidence matrix
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Upcoming Phases' });
  setTitle(slide, 'What evaluators will receive at project completion');
  addCue(slide, 'Final evidence combines prediction, data efficiency, rollout, control, and reproducibility without hiding failed runs.');
  const rows = [
    ['Prediction', 'Per-joint torque RMSE / MAE', 'ID + shoulder OOD + wrist OOD', C.accent1],
    ['Data efficiency', '10% / 30% / 100% learning curves', 'Seed-level uncertainty', C.accent2],
    ['Rollout', '2-second q and q̇ error', 'Divergence and final-state error', C.accent3],
    ['Control', 'Tracking RMSE and success / 10', 'Torque saturation + limits', C.accent6],
    ['Reproducibility', 'Locked code, data, configs, results', 'One-command regeneration', C.accent5],
  ];
  rows.forEach((r, i) => {
    const y = 1.24 + i * 0.91;
    addCard(slide, 0.78, y, 11.73, 0.72, { fill: i % 2 ? C.background2 : C.background1, line: r[3], shadow: false, objectName: `evidence-row-${i}` });
    addNode(slide, `${i + 1}`, 1.00, y + 0.14, 0.43, { fill: r[3], line: r[3], fontSize: 12, shadow: false });
    addText(slide, r[0], 1.68, y + 0.12, 1.68, 0.35, { fontFace: 'Cambria', fontSize: 16, bold: true });
    addText(slide, r[1], 3.70, y + 0.12, 3.40, 0.35, { fontSize: 12.2, color: C.text2 });
    addText(slide, r[2], 7.56, y + 0.12, 4.40, 0.35, { fontSize: 12.2, color: C.text2 });
  });
  addCard(slide, 0.78, 5.99, 7.44, 0.67, { fill: C.text1, line: C.text1, shadow: false, objectName: 'hypothesis-callout' });
  addText(slide, 'Hypothesis—not a promised outcome', 1.02, 6.12, 2.48, 0.25, { fontSize: 10.5, bold: true, color: C.accent2 });
  addText(slide, 'Physics structure should help most at low data and OOD.', 3.52, 6.10, 4.42, 0.28, { fontSize: 12.4, color: C.background1, align: 'center' });
  addCard(slide, 8.55, 5.99, 3.96, 0.67, { fill: C.background2, line: C.accent3, shadow: false, objectName: 'limitations-callout' });
  addText(slide, 'Scope: simulation • 2 DoF • no contact • clean derivatives', 8.84, 6.11, 3.39, 0.28, { fontSize: 10.5, color: C.text2, align: 'center' });
  addSource(slide, 'Every aggregate result will retain individual seeds/trials and failed runs');
  slide.addNotes('Speaking script:\nThe final project is judged across five evidence categories rather than one favorable loss value. We will report torque prediction, sample efficiency, two-second rollout, closed-loop tracking, and complete reproducibility. Individual seeds, trials, and failures remain visible. Our hypothesis is that physics helps most at low data and OOD, but a controlled negative result is still scientifically valid.');
}

// -----------------------------------------------------------------------------
// CLOSE
// -----------------------------------------------------------------------------
pptx.addSection({ title: 'Team and Close' });

// Slide 14 — Resources
{
  const slide = pptx.addSlide({ masterName: 'DARK', sectionTitle: 'Team and Close' });
  setTitle(slide, 'Primary sources and executable evidence');
  addCue(slide, 'Official sources define the plant, peer-reviewed work defines the method, and executable artifacts verify every claim.', true);
  const sources = [
    ['dm_control 1.0.52', 'reacher.py + reacher.xml', 'Plant, task, joints, damping, motors', C.accent1],
    ['MuJoCo 4.0.1 docs', 'computation + API + mjData', 'Equations, force spaces, inverse API', C.accent2],
    ['DeLaN / LNN / SMM', 'physics-informed learning papers', 'Architecture and fair comparison design', C.accent3],
    ['Project evidence', 'tests + validation + manifests', 'Every claim is reproducible from code', C.accent5],
  ];
  sources.forEach((s, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.82 + col * 6.15;
    const y = 1.30 + row * 2.40;
    addCard(slide, x, y, 5.55, 1.94, { fill: C.text2, transparency: 72, line: s[3], shadow: false, objectName: `source-card-${i}` });
    addNode(slide, `${i + 1}`, x + 0.27, y + 0.32, 0.58, { fill: s[3], line: s[3], fontSize: 15, shadow: false });
    addText(slide, s[0], x + 1.08, y + 0.22, 4.00, 0.38, { fontFace: 'Cambria', fontSize: 18, bold: true, color: C.background1 });
    addText(slide, s[1], x + 1.08, y + 0.70, 4.00, 0.26, { fontSize: 11, bold: true, color: s[3] });
    addText(slide, s[2], x + 1.08, y + 1.13, 4.00, 0.44, { fontSize: 12, color: C.background2, valign: 'top' });
  });
  addCard(slide, 2.40, 6.08, 8.52, 0.55, { fill: C.accent1, line: C.accent1, shadow: false, objectName: 'resource-close' });
  addText(slide, 'Detailed viva methodology and citations: docs/phase1_viva_handbook.md', 2.70, 6.19, 7.92, 0.27, { fontSize: 12, bold: true, color: C.text1, align: 'center' });
  addSource(slide, 'Official sources are versioned by release/tag; implementation evidence is stored with the project', true);
  slide.addNotes('Speaking script:\nOur plant facts come from the exact tagged dm_control source and MuJoCo documentation. The learning design comes from DeLaN, LNN, and structured mechanical-model literature. These references motivate the method, while our tests, manifests, and validation artifacts prove what this implementation actually does. Full citations and viva explanations are stored in the project handbook.');
}

// Slide 15 — Team and close
{
  const slide = pptx.addSlide({ masterName: 'LIGHT', sectionTitle: 'Team and Close' });
  setTitle(slide, 'Team • next checkpoint • questions');
  addCue(slide, 'Five team members share one reproducible pipeline; the next checkpoint is the complete learning-curve study.');
  const team = [
    ['AG', 'Aayush Gupta', '2023014', 'aayush23014@iiitd.ac.in', C.accent1],
    ['SM', 'Saksham Mishra', '2023471', 'saksham23471@iiitd.ac.in', C.accent2],
    ['SR', 'Shaman Ranjan', '2023498', 'shaman23498@iiitd.ac.in', C.accent3],
    ['AS', 'Aaman Sheikh', '2023006', 'aaman23006@iiitd.ac.in', C.accent6],
    ['MR', 'M Rayhan Khan', '2022269', 'rayhan22269@iiitd.ac.in', C.accent5],
  ];
  const positions = [
    [0.72, 1.30], [4.80, 1.30], [8.88, 1.30],
    [2.76, 3.55], [6.84, 3.55],
  ];
  team.forEach((m, i) => {
    const [x, y] = positions[i];
    addCard(slide, x, y, 3.72, 1.72, { fill: i % 2 ? C.background2 : C.background1, line: m[4], objectName: `team-card-${i}` });
    addNode(slide, m[0], x + 0.24, y + 0.32, 0.72, { fill: m[4], line: m[4], fontSize: 17, shadow: false });
    addText(slide, m[1], x + 1.18, y + 0.22, 2.20, 0.39, { fontFace: 'Cambria', fontSize: 17, bold: true });
    addText(slide, `Roll No. ${m[2]}`, x + 1.18, y + 0.70, 2.18, 0.25, { fontSize: 11.5, bold: true, color: C.text2 });
    addText(slide, m[3], x + 1.18, y + 1.08, 2.20, 0.28, { fontSize: 10.2, color: m[4] });
  });

  addCard(slide, 0.90, 5.86, 11.53, 0.78, { fill: C.text1, line: C.text1, shadow: false, objectName: 'closing-statement' });
  addText(slide, 'Phase 1 is complete and trustworthy.', 1.20, 5.98, 3.37, 0.32, { fontFace: 'Cambria', fontSize: 18, bold: true, color: C.accent1 });
  addText(slide, 'Next checkpoint: trained baselines, learning curves, and 2-second rollout evidence.', 4.66, 5.96, 6.98, 0.34, { fontSize: 13, color: C.background1, align: 'center' });
  addPill(slide, 'QUESTIONS', 10.96, 0.46, 1.22, { fill: C.accent1, color: C.text1, fontSize: 9 });
  addJointMotif(slide, 11.55, 6.38, 0.50, false);
  slide.addNotes('Closing script:\nOur five-member team shares one reproducible code and evidence pipeline. At this checkpoint, Phase 1 is complete and trustworthy. Our immediate next milestone is to train every baseline and produce the full 10, 30, and 100 percent learning curves and rollout comparison. After that, we will integrate the controllers and final live demonstration. Thank you—we welcome questions.');
}

async function build() {
  await pptx.writeFile({ fileName: OUTPUT });
  await applyTheme(OUTPUT, THEME);
  console.log(`Wrote ${OUTPUT}`);
}

build().catch((error) => {
  console.error(error);
  process.exit(1);
});
