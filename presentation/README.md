# Project presentation

Evaluator-facing PowerPoint:

[`output/Reacher_Inverse_Dynamics_Project_Presentation.pptx`](output/Reacher_Inverse_Dynamics_Project_Presentation.pptx)

The 15-slide deck includes:

- the inverse-dynamics problem and practical motivation;
- the exact `dm_control` reacher plant;
- analytical, Lagrangian, and black-box comparisons;
- the three implementation phases;
- completed Phase 1 methodology and validation evidence;
- upcoming model-training and closed-loop-control work;
- final evaluation criteria;
- primary resource categories;
- all team names, roll numbers, and email addresses;
- visible key-message cues and detailed PowerPoint speaker notes.

## Rebuild

```bash
cd presentation
npm install
npm run build
```

Generator source: `build_deck.js`  
Rendered reacher image: `assets/reacher_render.png`

## Validation

The generated deck passes the PowerPoint package/schema validator and content extraction checks. A PDF preview is available locally under `rendered/`.
