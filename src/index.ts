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

import { InputDialog, showErrorMessage } from '@jupyterlab/apputils';

import { ITranslator } from '@jupyterlab/translation';

import { S3Drive } from './contents';

import { S3FileBrowser } from './browser';

import { minioIcon } from './icons';

import { t, setLocale } from './i18n';

import * as s3 from './s3';

import { showS3PathPickerDialog, showLocalPathInputDialog } from './dialogs';

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
    ISettingRegistry,
    ITranslator
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
  settingRegistry: ISettingRegistry,
  translator: ITranslator | null
): void {
  // Set locale based on JupyterLab's language setting
  if (translator) {
    const langCode = translator.languageCode;
    if (langCode && langCode !== 'en') {
      setLocale(langCode);
    }
  }

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
  s3Browser.title.caption = t('sidebar.caption');

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
    label: t('command.createBucket'),
    isVisible: () => getCurrentS3Path() === '',
    execute: async () => {
      const result = await InputDialog.getText({
        title: t('dialog.createBucket'),
        label: t('dialog.bucketNameLabel'),
        placeholder: t('dialog.bucketNamePlaceholder')
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
              t('error.bucketCreation'),
              Error(response.message)
            );
          } else {
            browser.model.refresh();
          }
        } catch (err: any) {
          void showErrorMessage(t('error.bucketCreation'), err);
        }
      }
    }
  });

  app.commands.addCommand('minio:delete-bucket', {
    label: t('command.deleteBucket'),
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
            t('error.bucketDeletion'),
            Error(response.message)
          );
        } else {
          browser.model.refresh();
        }
      } catch (err: any) {
        void showErrorMessage(t('error.bucketDeletion'), err);
      }
    }
  });

  // --- Phase 2: Cross-bucket copy/move commands ---

  app.commands.addCommand('minio:copy-to-path', {
    label: t('command.copyToPath'),
    isVisible: () => getSelectedS3Path() !== null,
    execute: async () => {
      const selected = getSelectedS3Path();
      if (!selected) {
        return;
      }
      const dest = await showS3PathPickerDialog(
        t('dialog.copyToS3Path'),
        ''
      );
      if (dest !== null) {
        const fileName = selected.split('/').pop() || selected;
        const destPath = dest ? dest + '/' + fileName : fileName;
        try {
          const response: any = await s3.copyFile(selected, destPath);
          if (response.error) {
            void showErrorMessage(t('error.copy'), Error(response.message));
          } else {
            browser.model.refresh();
          }
        } catch (err: any) {
          void showErrorMessage(t('error.copy'), err);
        }
      }
    }
  });

  app.commands.addCommand('minio:move-to-path', {
    label: t('command.moveToPath'),
    isVisible: () => getSelectedS3Path() !== null,
    execute: async () => {
      const selected = getSelectedS3Path();
      if (!selected) {
        return;
      }
      const dest = await showS3PathPickerDialog(
        t('dialog.moveToS3Path'),
        ''
      );
      if (dest !== null) {
        const fileName = selected.split('/').pop() || selected;
        const destPath = dest ? dest + '/' + fileName : fileName;
        try {
          const response: any = await s3.moveFile(selected, destPath);
          if (response.error) {
            void showErrorMessage(t('error.move'), Error(response.message));
          } else {
            browser.model.refresh();
          }
        } catch (err: any) {
          void showErrorMessage(t('error.move'), err);
        }
      }
    }
  });

  // --- Phase 3: S3 <-> Local transfer commands ---

  app.commands.addCommand('minio:copy-to-local', {
    label: t('command.copyToLocal'),
    isVisible: () => getSelectedS3Path() !== null,
    execute: async () => {
      const selected = getSelectedS3Path();
      if (!selected) {
        return;
      }
      const fileName = selected.split('/').pop() || selected;
      const localPath = await showLocalPathInputDialog(
        t('dialog.copyS3ToLocal'),
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
            void showErrorMessage(
              t('error.transfer'),
              Error(response.message)
            );
          }
        } catch (err: any) {
          void showErrorMessage(t('error.transfer'), err);
        }
      }
    }
  });

  app.commands.addCommand('minio:copy-to-s3', {
    label: t('command.copyToS3'),
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
        t('dialog.copyLocalToS3'),
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
            void showErrorMessage(
              t('error.transfer'),
              Error(response.message)
            );
          }
        } catch (err: any) {
          void showErrorMessage(t('error.transfer'), err);
        }
      }
    }
  });

  // --- Delete from S3 command ---

  app.commands.addCommand('minio:delete', {
    label: t('command.deleteFromS3'),
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
        title: t('dialog.deleteFromS3'),
        label: `${t('dialog.deleteConfirm')} ${names} ?`
      });
      if (result.button.accept && result.value) {
        for (const itemPath of items) {
          try {
            const response = await s3.deleteFile(itemPath);
            if (response.error) {
              void showErrorMessage(
                t('error.delete'),
                Error(
                  response.message ||
                    `${t('error.deleteFailed')} ${itemPath}`
                )
              );
            }
          } catch (err: any) {
            void showErrorMessage(t('error.delete'), err);
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
    selector:
      '.jp-DirListing-item:not(#minio-file-browser .jp-DirListing-item)',
    rank: 100
  });

  return;
}

export default fileBrowserPlugin;
