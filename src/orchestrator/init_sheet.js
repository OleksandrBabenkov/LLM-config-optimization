/**
 * Initializes the Master Tracker Sheet with the required headers for Task 3.2.
 * This script should be run once from the Apps Script editor attached to the Master Tracker Sheet.
 */
function initializeMasterTrackerHeaders() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheets()[0]; // Target the first sheet
  
  // Define the schema as per Task 3.2
  const headers = [
    'Timestamp',
    'Iteration_ID',
    'Experiment_Type',
    'Config_Filename',
    'Results_Filename',
    'PSNR',
    'SSIM',
    'Status',
    'Error_Message',
    'LLM_Reasoning'
  ];
  
  // Clear any existing content and set the headers in the first row
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  // Apply formatting for better readability
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setBackground('#444444')
             .setFontColor('#ffffff')
             .setFontWeight('bold')
             .setHorizontalAlignment('center')
             .setVerticalAlignment('middle');
             
  // Freeze the first row to keep headers visible when scrolling
  sheet.setFrozenRows(1);
  
  // Auto-resize columns to fit headers
  sheet.autoResizeColumns(1, headers.length);
  
  Logger.log('Master Tracker Sheet headers initialized successfully.');
}

/**
 * Helper function to create the folder structure if IDs are not provided.
 * (Optional automation for Task 3.1)
 */
function setupProjectWorkspace() {
  const rootName = 'Image_Optimization_Pipeline';
  const folders = DriveApp.getFoldersByName(rootName);
  let rootFolder;
  
  if (folders.hasNext()) {
    rootFolder = folders.next();
  } else {
    rootFolder = DriveApp.createFolder(rootName);
  }
  
  const subfolders = ['LLM_Configs_In', 'Python_Results_Out'];
  subfolders.forEach(name => {
    const existing = rootFolder.getFoldersByName(name);
    if (!existing.hasNext()) {
      rootFolder.createFolder(name);
    }
  });
  
  Logger.log('Workspace folders verified/created in ' + rootFolder.getName());
}
