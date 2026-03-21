import {
  ILayoutRestorer,
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { ISettingRegistry } from '@jupyterlab/settingregistry';

import { IDocumentManager } from '@jupyterlab/docmanager';

import {
  IDefaultFileBrowser,
  IFileBrowserFactory
} from '@jupyterlab/filebrowser';

import {
  InputDialog,
  showErrorMessage
} from '@jupyterlab/apputils';

import { S3Drive } from './contents';

import { S3FileBrowser } from './browser';

import { minioIcon } from './icons';

import * as s3 from './s3';

import {
  showS3PathPickerDialog,
  showLocalPathInputDialog
} from './dialogs';

/**
 * S3 filebrowser plugin state namespace.
 */
const NAMESPACE = 'minio-filebrowser';

/**
 * The ID for the plugin.
 */
const PLUGIN_ID = 'jupyterlab-minio:plugin';

/**
 * Initialization data for the jupyterlab-minio extension.
 */
const fileBrowserPlugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  autoStart: true,
  optional: [
    IDefaultFileBrowser,
    IDocumentManager,
    IFileBrowserFactory,
    ILayoutRestorer,
    ISettingRegistry
  ],
  activate: activateFileBrowser
};

/**
 * Activate the file browser.
 */
function activateFileBrowser(
  app: JupyterFrontEnd,
  defaultBrowser: IDefaultFileBrowser | null,
  manager: IDocumentManager,
  factory: IFileBrowserFactory,
  restorer: ILayoutRestorer,
  settingRegistry: ISettingRegistry
): void {
  // Add the S3 backend to the contents manager.
  const drive = new S3Drive(app.docRegistry);
  manager.services.contents.addDrive(drive);

  const browser = factory.createFileBrowser(NAMESPACE, {
    driveName: drive.name,
    state: null,
    refreshInterval: 300000
  });

  const s3Browser = new S3FileBrowser(browser, drive, manager);

  s3Browser.title.icon = minioIcon;
  s3Browser.title.caption = 'Minio Browser';

  s3Browser.id = 'minio-file-browser';

  // Add the file browser widget to the application restorer.
  restorer.add(s3Browser, NAMESPACE);
  app.shell.add(s3Browser, 'left', { rank: 100 });

  // Helper to get the selected item path from the S3 browser
  const getSelectedS3Path = (): string | null => {
    const item = browser.selectedItems().next();
    if (item && item.value) {
      return (item.value as any).path || null;
    }
    return null;
  };

  // Helper to get current browser path (strip drive prefix)
  const getCurrentS3Path = (): string => {
    const path = browser.model.path;
    // Remove the drive prefix "S3:" if present
    return path.replace(/^S3:/, '');
  };

  // --- Phase 1: Bucket commands ---

  app.commands.addCommand('minio:create-bucket', {
    label: 'Create Bucket',
    isVisible: () => getCurrentS3Path() === '',
    execute: async () => {
      const result = await InputDialog.getText({
        title: 'Create New Bucket',
        label: 'Bucket name (lowercase, 3-63 chars, alphanumeric and hyphens):',
        placeholder: 'my-bucket-name'
      });
      if (result.button.accept && result.value) {
        const name = result.value.trim();
        if (!name) {
          return;
        }
        try {
          const response = await s3.createBucket(name);
          if (response.error) {
            void showErrorMessage(
              'Bucket Creation Error',
              Error(response.message)
            );
          } else {
            browser.model.refresh();
          }
        } catch (err: any) {
          void showErrorMessage('Bucket Creation Error', err);
        }
      }
    }
  });

  app.commands.addCommand('minio:delete-bucket', {
    label: 'Delete Bucket',
    isVisible: () => {
      const selected = getSelectedS3Path();
      // A bucket path has no slash
      return selected !== null && !selected.includes('/');
    },
    execute: async () => {
      const selected = getSelectedS3Path();
      if (!selected) {
        return;
      }
      const bucketName = selected.replace(/\/$/, '');
      try {
        const response = await s3.deleteBucket(bucketName);
        if (response.error) {
          void showErrorMessage(
            'Bucket Deletion Error',
            Error(response.message)
          );
        } else {
          browser.model.refresh();
        }
      } catch (err: any) {
        void showErrorMessage('Bucket Deletion Error', err);
      }
    }
  });

  // --- Phase 2: Cross-bucket copy/move commands ---

  app.commands.addCommand('minio:copy-to-path', {
    label: 'Copy to S3 Path...',
    isVisible: () => getSelectedS3Path() !== null,
    execute: async () => {
      const selected = getSelectedS3Path();
      if (!selected) {
        return;
      }
      const dest = await showS3PathPickerDialog(
        'Copy to S3 Path',
        ''
      );
      if (dest !== null) {
        const fileName = selected.split('/').pop() || selected;
        const destPath = dest ? dest + '/' + fileName : fileName;
        try {
          const response: any = await s3.copyFile(selected, destPath);
          if (response.error) {
            void showErrorMessage('Copy Error', Error(response.message));
          } else {
            browser.model.refresh();
          }
        } catch (err: any) {
          void showErrorMessage('Copy Error', err);
        }
      }
    }
  });

  app.commands.addCommand('minio:move-to-path', {
    label: 'Move to S3 Path...',
    isVisible: () => getSelectedS3Path() !== null,
    execute: async () => {
      const selected = getSelectedS3Path();
      if (!selected) {
        return;
      }
      const dest = await showS3PathPickerDialog(
        'Move to S3 Path',
        ''
      );
      if (dest !== null) {
        const fileName = selected.split('/').pop() || selected;
        const destPath = dest ? dest + '/' + fileName : fileName;
        try {
          const response: any = await s3.moveFile(selected, destPath);
          if (response.error) {
            void showErrorMessage('Move Error', Error(response.message));
          } else {
            browser.model.refresh();
          }
        } catch (err: any) {
          void showErrorMessage('Move Error', err);
        }
      }
    }
  });

  // --- Phase 3: S3 <-> Local transfer commands ---

  app.commands.addCommand('minio:copy-to-local', {
    label: 'Copy to Local Filesystem...',
    isVisible: () => getSelectedS3Path() !== null,
    execute: async () => {
      const selected = getSelectedS3Path();
      if (!selected) {
        return;
      }
      const fileName = selected.split('/').pop() || selected;
      const localPath = await showLocalPathInputDialog(
        'Copy S3 File to Local',
        fileName
      );
      if (localPath) {
        try {
          const response = await s3.transferFile(
            's3',
            selected,
            'local',
            localPath
          );
          if (response.error) {
            void showErrorMessage('Transfer Error', Error(response.message));
          }
        } catch (err: any) {
          void showErrorMessage('Transfer Error', err);
        }
      }
    }
  });

  app.commands.addCommand('minio:copy-to-s3', {
    label: 'Copy to S3...',
    isVisible: () => defaultBrowser !== null,
    execute: async () => {
      if (!defaultBrowser) {
        return;
      }
      const item = defaultBrowser.selectedItems().next();
      const localPath = item && item.value ? (item.value as any).path : null;
      if (!localPath) {
        return;
      }
      const dest = await showS3PathPickerDialog(
        'Copy Local File to S3',
        ''
      );
      if (dest !== null) {
        const fileName = localPath.split('/').pop() || localPath;
        const destPath = dest ? dest + '/' + fileName : fileName;
        try {
          const response = await s3.transferFile(
            'local',
            localPath,
            's3',
            destPath
          );
          if (response.error) {
            void showErrorMessage('Transfer Error', Error(response.message));
          }
        } catch (err: any) {
          void showErrorMessage('Transfer Error', err);
        }
      }
    }
  });

  // --- Delete from S3 command ---

  app.commands.addCommand('minio:delete', {
    label: 'Delete from S3',
    isVisible: () => getSelectedS3Path() !== null,
    execute: async () => {
      const items: string[] = [];
      const iter = browser.selectedItems();
      let next = iter.next();
      while (next && next.value) {
        const rawPath = (next.value as any).path as string;
        // Strip drive prefix "S3:" if present
        items.push(rawPath.replace(/^S3:/, ''));
        next = iter.next();
      }
      if (items.length === 0) {
        return;
      }
      const names = items.map(p => p.split('/').pop() || p).join(', ');
      const result = await InputDialog.getBoolean({
        title: 'Delete from S3',
        label: `Are you sure you want to delete: ${names}?`
      });
      if (result.button.accept && result.value) {
        for (const itemPath of items) {
          try {
            const response = await s3.deleteFile(itemPath);
            if (response.error) {
              void showErrorMessage(
                'Delete Error',
                Error(response.message || `Failed to delete ${itemPath}`)
              );
            }
          } catch (err: any) {
            void showErrorMessage('Delete Error', err);
          }
        }
        browser.model.refresh();
      }
    }
  });

  // --- Context menu items for the S3 file browser ---

  app.contextMenu.addItem({
    command: 'minio:create-bucket',
    selector: '#minio-file-browser .jp-DirListing-content',
    rank: 1
  });

  app.contextMenu.addItem({
    command: 'minio:delete-bucket',
    selector: '#minio-file-browser .jp-DirListing-item',
    rank: 2
  });

  app.contextMenu.addItem({
    command: 'minio:copy-to-path',
    selector: '#minio-file-browser .jp-DirListing-item',
    rank: 3
  });

  app.contextMenu.addItem({
    command: 'minio:move-to-path',
    selector: '#minio-file-browser .jp-DirListing-item',
    rank: 4
  });

  app.contextMenu.addItem({
    command: 'minio:copy-to-local',
    selector: '#minio-file-browser .jp-DirListing-item',
    rank: 5
  });

  app.contextMenu.addItem({
    command: 'minio:delete',
    selector: '#minio-file-browser .jp-DirListing-item',
    rank: 6
  });

  // Context menu item for default JupyterLab file browser -> Copy to S3
  app.contextMenu.addItem({
    command: 'minio:copy-to-s3',
    selector: '.jp-DirListing-item:not(#minio-file-browser .jp-DirListing-item)',
    rank: 100
  });

  return;
}

export default fileBrowserPlugin;
