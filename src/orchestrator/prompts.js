/**
 * LLM Cognitive Architecture: Prompts and Schemas
 * Defines the persona, output format, and context structure for the AI Researcher loop.
 */

const SYSTEM_PROMPT = `
You are a Senior Computer Vision Researcher specializing in autonomous image restoration and filtering.
Your objective is to discover optimal mathematical image filters through iterative experimentation.

### GOALS
1. Maximize Peak Signal-to-Noise Ratio (PSNR).
2. Maximize Structural Similarity Index (SSIM).
3. Discover novel kernel configurations that outperform standard baseline filters (e.g., Gaussian, Sobel).

### OPERATIONAL CONSTRAINTS
- Output ONLY valid JSON according to the provided schema.
- Your "reasoning" field must contain a technical, mathematical justification for the proposed parameters.
- Focus on the relationship between kernel weights and high-frequency noise suppression or edge preservation.
- Do not provide conversational filler or explanations outside the JSON object.

### SCIENTIFIC METHOD
Analyze the historical results provided in the context. Formulate a hypothesis on why previous kernels succeeded or failed, then propose a new kernel that explores the parameter space or exploits a discovered pattern.
`;

const EXPERIMENT_CONFIG_SCHEMA = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "experiment_type": {
      "type": "string",
      "enum": ["kernel_filter"],
      "description": "The class name of the experiment to execute."
    },
    "parameters": {
      "type": "object",
      "properties": {
        "kernel": {
          "type": "array",
          "items": {
            "type": "array",
            "items": { "type": "number" }
          },
          "description": "An NxN matrix (e.g., 3x3, 5x5, 7x7) representing the convolution kernel. Must be a square matrix."
        },
        "target_images": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of images to process (e.g., ['lena', 'cameraman', 'pneumoniamnist'])."
        },
        "target_size": {
          "type": "array",
          "items": { "type": "integer" },
          "minItems": 2,
          "maxItems": 2,
          "description": "Resolution for processing [width, height]."
        }
      },
      "required": ["kernel"]
    },
    "reasoning": {
      "type": "string",
      "description": "A concise technical rationale for the chosen kernel parameters."
    }
  },
  "required": ["experiment_type", "parameters", "reasoning"],
  "additionalProperties": false
};

const HALL_OF_FAME_TEMPLATE = `
### HALL OF FAME (Top 3 Configurations)
The following experiments yielded the highest average PSNR/SSIM metrics recorded so far:

| Rank | Iteration ID | Avg PSNR | Avg SSIM | Mathematical Reasoning |
| :--- | :--- | :--- | :--- | :--- |
{{hall_of_fame_rows}}

### RECENT ITERATIONS
Context from the last 5 experiments to prevent cognitive drift:

| Iteration ID | Avg PSNR | Avg SSIM | Status |
| :--- | :--- | :--- | :--- |
{{recent_iteration_rows}}
`;

const FALLBACK_PROMPT = `
### ERROR DETECTED: INVALID OUTPUT
Your previous response could not be processed due to a structural or logical error.

**Error Details:**
{{error_message}}

**Task:**
Analyze the error and the historical results. Refine your kernel design to ensure it is both mathematically sound and adheres strictly to the JSON schema.
Provide ONLY the corrected JSON object.
`;

// Export for GAS (Note: GAS doesn't use module.exports, it uses global scope)
// We keep them as constants so they are accessible from other .gs files.
