/**
 * GOOGLE APPS SCRIPT ORCHESTRATOR - MAIN CONTROL LOOP
 * 
 * SETUP INSTRUCTIONS:
 * 1. Open the Google Sheet associated with this project.
 * 2. Go to Extensions -> Apps Script.
 * 3. Copy the contents of prompts.js, init_sheet.js, and main.js into the editor.
 * 4. Set Script Properties (Project Settings -> Script Properties):
 *    - GEMINI_API_KEY: Your Google AI Studio API Key.
 * 5. Initialize the sheet by running initializeMasterTrackerHeaders() from init_sheet.js.
 * 6. Set up a Time-driven Trigger:
 *    - Go to Triggers (clock icon).
 *    - Add Trigger -> Choose 'orchestrate' function.
 *    - Event source: Time-driven.
 *    - Type: Minutes timer (e.g., every 15 or 30 minutes).
 */

const ROOT_FOLDER_NAME = 'LLM-config-optimization';
const RESULTS_FOLDER_NAME = 'Python_Results_Out';
const CONFIGS_FOLDER_NAME = 'LLM_Configs_In';

/**
 * Main entry point for the orchestration loop.
 */
function orchestrate() {
  Logger.log('Starting Orchestration Loop...');
  
  // 1. Ingest new results from Python workers
  processNewResults();
  
  // 2. Call the AI Researcher to generate the next configuration
  callAiResearcher();
  
  Logger.log('Orchestration Loop Completed.');
}

/**
 * CSV Ingestion: Scans for result CSVs and appends them to the Master Tracker.
 */
function processNewResults() {
  const rootFolder = getFolderByName(ROOT_FOLDER_NAME);
  const resultsFolder = getSubFolder(rootFolder, RESULTS_FOLDER_NAME);
  const files = resultsFolder.getFilesByType(MimeType.CSV);
  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheets()[0];
  
  while (files.hasNext()) {
    const file = files.next();
    const csvData = Utilities.parseCsv(file.getBlob().getDataAsString());
    
    // Skip header row and append data
    if (csvData.length > 1) {
      const headers = csvData[0];
      const iterationIdIdx = headers.indexOf('Iteration_ID');
      
      const rows = csvData.slice(1);
      const uniqueRows = rows.filter(row => {
        const iterationId = iterationIdIdx !== -1 ? row[iterationIdIdx] : null;
        return !isIterationLogged(iterationId);
      });

      if (uniqueRows.length > 0) {
        sheet.getRange(sheet.getLastRow() + 1, 1, uniqueRows.length, uniqueRows[0].length).setValues(uniqueRows);
        Logger.log('Ingested ' + uniqueRows.length + ' unique rows from ' + file.getName());
      } else {
        Logger.log('Skipped duplicate results in ' + file.getName());
      }
    }
    
    // Delete processed file
    file.setTrashed(true);
  }
}

/**
 * LLM Researcher Loop: Consults Gemini API to propose new kernel configurations.
 */
function callAiResearcher() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheets()[0];
  const data = sheet.getDataRange().getValues();
  
  if (data.length <= 1) {
    Logger.log('No data found in Master Tracker to build context.');
    // If no data, we can still call it with an empty context or a baseline.
  }
  
  // Build context for Hall of Fame and Recent Iterations
  const context = buildContext(data);
  const prompt = SYSTEM_PROMPT + '\n\n' + context;
  
  let aiResponse;
  try {
    aiResponse = fetchGeminiCompletion(prompt);
  } catch (e) {
    Logger.log('Error calling Gemini API: ' + e.message);
    return;
  }
  
  // Robustness: Hallucination Guard
  let parsedConfig;
  try {
    parsedConfig = parseLlmResponse(aiResponse);
  } catch (e) {
    Logger.log('Malformed JSON detected. Triggering Fallback Retry...');
    const retryPrompt = FALLBACK_PROMPT.replace('{{error_message}}', e.message);
    try {
      aiResponse = fetchGeminiCompletion(prompt + '\n\n' + retryPrompt);
      parsedConfig = parseLlmResponse(aiResponse);
    } catch (retryError) {
      Logger.log('Critical Error: Hallucination Guard failed to recover. ' + retryError.message);
      return;
    }
  }
  
  // Save new config
  saveConfigAsJson(parsedConfig);
}

/**
 * Builds the Hall of Fame and Recent Iterations context from sheet data.
 */
function buildContext(data) {
  if (data.length <= 1) return 'No historical data available yet. Propose the first experimental configuration.';
  
  const headers = data[0];
  const rows = data.slice(1);
  
  // Indices based on headers
  const psnrIdx = headers.indexOf('PSNR');
  const ssimIdx = headers.indexOf('SSIM');
  const idIdx = headers.indexOf('Iteration_ID');
  const reasonIdx = headers.indexOf('LLM_Reasoning');
  const statusIdx = headers.indexOf('Status');

  // Filter successful experiments
  const successfulRows = rows.filter(r => r[statusIdx] === 'SUCCESS');
  
  // Top 3 (Hall of Fame) - Sorted by PSNR (assuming higher is better)
  const hallOfFame = successfulRows
    .sort((a, b) => b[psnrIdx] - a[psnrIdx])
    .slice(0, 3)
    .map((r, i) => `| ${i+1} | ${r[idIdx]} | ${r[psnrIdx].toFixed(4)} | ${r[ssimIdx].toFixed(4)} | ${r[reasonIdx]} |`)
    .join('\n');

  // Recent 5
  const recent = rows
    .slice(-5)
    .reverse()
    .map(r => `| ${r[idIdx]} | ${r[psnrIdx] ? r[psnrIdx].toFixed(4) : 'N/A'} | ${r[ssimIdx] ? r[ssimIdx].toFixed(4) : 'N/A'} | ${r[statusIdx]} |`)
    .join('\n');

  return HALL_OF_FAME_TEMPLATE
    .replace('{{hall_of_fame_rows}}', hallOfFame || 'No successful experiments yet.')
    .replace('{{recent_iteration_rows}}', recent || 'No recent experiments.');
}

/**
 * Calls Gemini API via UrlFetchApp.
 */
function fetchGeminiCompletion(prompt) {
  const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY not found in Script Properties.');
  
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
  
  const payload = {
    contents: [{
      parts: [{ text: prompt }]
    }],
    generationConfig: {
      temperature: 0.7,
      topP: 0.95,
      topK: 40,
      maxOutputTokens: 4096,
      response_mime_type: "application/json",
      response_schema: EXPERIMENT_CONFIG_SCHEMA
    }
  };
  
  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  let response;
  try {
    response = UrlFetchApp.fetch(url, options);
  } catch (e) {
    throw new Error('Network error calling Gemini API: ' + e.message);
  }

  const responseCode = response.getResponseCode();
  const responseText = response.getContentText();

  if (responseCode !== 200) {
    Logger.log('Gemini API Error. Status: ' + responseCode);
    Logger.log('Response body: ' + responseText);
    throw new Error('Gemini API returned status ' + responseCode);
  }

  const json = JSON.parse(responseText);
  
  if (json.candidates && json.candidates[0] && json.candidates[0].content && json.candidates[0].content.parts[0]) {
    return json.candidates[0].content.parts[0].text;
  } else {
    throw new Error('Unexpected API response format: ' + JSON.stringify(json));
  }
}

/**
 * Parses and cleans LLM response to extract JSON.
 */
function parseLlmResponse(text) {
  let cleanJson = text;
  
  // 1. Strip markdown code blocks if present
  if (cleanJson.includes('```')) {
    cleanJson = cleanJson.replace(/```json/g, '').replace(/```/g, '');
  }
  
  // 2. Greedy extraction: find first '{' and last '}'
  const firstBrace = cleanJson.indexOf('{');
  const lastBrace = cleanJson.lastIndexOf('}');
  
  if (firstBrace === -1 || lastBrace === -1 || lastBrace < firstBrace) {
    Logger.log('FAILED TO EXTRACT JSON. Raw length: ' + text.length);
    Logger.log('First 100: ' + text.substring(0, 100));
    Logger.log('Last 100: ' + text.substring(text.length - 100));
    throw new Error('No valid JSON object found in response.');
  }
  
  cleanJson = cleanJson.substring(firstBrace, lastBrace + 1);
  
  let parsed;
  try {
    parsed = JSON.parse(cleanJson);
  } catch (e) {
    Logger.log('JSON PARSE ERROR: ' + e.message);
    Logger.log('Raw length: ' + text.length);
    Logger.log('First 100: ' + text.substring(0, 100));
    Logger.log('Last 100: ' + text.substring(text.length - 100));
    throw new Error('Malformed JSON: ' + e.message);
  }
  
  // Basic validation against schema requirements
  if (!parsed.experiment_type || !parsed.parameters || !parsed.parameters.kernel) {
    throw new Error('JSON missing required fields: experiment_type, parameters.kernel');
  }
  
  return parsed;
}

/**
 * Saves the configuration as a JSON file with a unique Iteration ID.
 */
function saveConfigAsJson(config) {
  const rootFolder = getFolderByName(ROOT_FOLDER_NAME);
  const configsFolder = getSubFolder(rootFolder, CONFIGS_FOLDER_NAME);
  
  const iterationId = 'ITER-' + Utilities.formatDate(new Date(), 'GMT', 'yyyyMMdd-HHmmss') + '-' + Math.floor(Math.random() * 1000);
  config.iteration_id = iterationId; // Inject ID into config
  
  const filename = `${iterationId}.json`;
  configsFolder.createFile(filename, JSON.stringify(config, null, 2), MimeType.PLAIN_TEXT);
  Logger.log('Saved new configuration: ' + filename);
}

/**
 * Helper: Find folder by name or throw error.
 */
function getFolderByName(name) {
  const folders = DriveApp.getFoldersByName(name);
  if (folders.hasNext()) return folders.next();
  throw new Error('Folder not found: ' + name);
}

/**
 * Helper: Get or Create subfolder.
 */
function getSubFolder(parentFolder, name) {
  const folders = parentFolder.getFoldersByName(name);
  if (folders.hasNext()) return folders.next();
  return parentFolder.createFolder(name);
}

/**
 * Checks if an Iteration_ID already exists in the Master Tracker sheet.
 * This provides idempotency for sheet logging.
 */
function isIterationLogged(iterationId) {
  if (!iterationId) return false;
  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheets()[0];
  const lastRow = sheet.getLastRow();
  
  if (lastRow <= 1) return false;
  
  // Optimization: Only fetch the Iteration_ID column (Column B, index 2)
  const ids = sheet.getRange(2, 2, lastRow - 1, 1).getValues();
  return ids.flat().some(id => id === iterationId);
}
