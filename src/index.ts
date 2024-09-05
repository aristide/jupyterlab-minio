import {
  ILayoutRestorer,
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import {
  Clipboard,
  createToolbarFactory,
  ICommandPalette,
  InputDialog,
  IToolbarWidgetRegistry,
  MainAreaWidget,
  setToolbar,
  showErrorMessage,
  WidgetTracker
} from '@jupyterlab/apputils';

import { ISettingRegistry } from '@jupyterlab/settingregistry';

import { IDocumentManager } from "@jupyterlab/docmanager";

import { IFileBrowserFactory } from "@jupyterlab/filebrowser";

import { ITranslator } from '@jupyterlab/translation';

import { S3Drive } from "./contents";

import { S3FileBrowser } from "./browser";

/**
 * S3 filebrowser plugin state namespace.
 */
const NAMESPACE = "minio-filebrowser";

/**
 * The ID for the plugin.
 */
const PLUGIN_ID = "jupyterlab-minio:plugin";


/**
 * Initialization data for the jupyterlab-minio extension.
 */
const fileBrowserPlugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  autoStart: true,
  optional: [
    IDocumentManager,
    IFileBrowserFactory,
    ILayoutRestorer,
    ISettingRegistry,
    ITranslator,
    ICommandPalette
  ],
  activate: activateFileBrowser
};
/**
 * Activate the file browser.
 */
function activateFileBrowser(
  app: JupyterFrontEnd,
  manager: IDocumentManager,
  factory: IFileBrowserFactory,
  restorer: ILayoutRestorer,
  settingRegistry: ISettingRegistry,
  translator: ITranslator,
  commandPalette: ICommandPalette | null
): void {
  // Add the S3 backend to the contents manager.
  const drive = new S3Drive(app.docRegistry);
  manager.services.contents.addDrive(drive);

  const browser = factory.createFileBrowser(NAMESPACE, {
    driveName: drive.name,
    state: null,
    refreshInterval: 300000,
  });

  const s3Browser = new S3FileBrowser(browser, drive, manager);

  s3Browser.title.iconClass = "jp-S3-icon jp-SideBar-tabIcon";
  s3Browser.title.caption = "Minio Browser";

  s3Browser.id = "s3-file-browser";

  // Add the file browser widget to the application restorer.
  restorer.add(s3Browser, NAMESPACE);
  app.shell.add(s3Browser, "left", { rank: 501 });

  return;
}

function addCommands(
  app: JupyterFrontEnd,
  factory: IFileBrowserFactory,
  translator: ITranslator,
  settingRegistry: ISettingRegistry | null,
  commandPalette: ICommandPalette | null
): void {
  const trans = translator.load('jupyterlab');
  const { docRegistry: registry, commands } = app;
  const { defaultBrowser: browser, tracker } = factory;
}

export default fileBrowserPlugin;
