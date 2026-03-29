import { PanelLayout, Widget } from '@lumino/widgets';

import { FileBrowser } from '@jupyterlab/filebrowser';

import { S3Drive } from './contents';

import { IDocumentManager } from '@jupyterlab/docmanager';

import { ServerConnection, ServiceManager } from '@jupyterlab/services';

import { URLExt } from '@jupyterlab/coreutils';

import { showErrorMessage } from '@jupyterlab/apputils';

import {
  ToolbarButton,
  showDialog,
  Dialog,
  InputDialog
} from '@jupyterlab/apputils';

import {
  settingsIcon,
  refreshIcon,
  addIcon,
  fileUploadIcon,
  filterListIcon,
  newFolderIcon
} from '@jupyterlab/ui-components';

import { minioIcon } from './icons';

import { t } from './i18n';

import * as s3 from './s3';

import { restartAllWithNotification } from './env-sync';

/**
 * Widget for authenticating against
 * an s3 object storage instance.
 */
let s3AuthenticationForm: any | undefined | null;

/**
 * Widget for hosting the S3 filebrowser.
 */
export class S3FileBrowser extends Widget {
  private _serviceManager: ServiceManager.IManager;

  constructor(
    browser: FileBrowser,
    drive: S3Drive,
    manager: IDocumentManager,
    serviceManager: ServiceManager.IManager
  ) {
    super();
    this._serviceManager = serviceManager;
    this.addClass('jp-S3Browser');
    this.layout = new PanelLayout();

    // edit Config Button
    const editConfigButton = new ToolbarButton({
      icon: settingsIcon,
      tooltip: t('toolbar.resetCredentials'),
      onClick: async () => {
        const result = await showDialog({
          title: t('dialog.confirmRequired'),
          body: t('dialog.confirmResetBody'),
          buttons: [
            Dialog.cancelButton(),
            Dialog.okButton({ label: t('dialog.confirm') })
          ]
        });

        if (result.button.accept) {
          console.log('Configuration confirmed.');
          Private.deleteConfigFile().then(({ success, message }) => {
            if (success) {
              (this.layout as PanelLayout).removeWidget(browser);
              (this.layout as PanelLayout).addWidget(s3AuthenticationForm);
              restartAllWithNotification(this._serviceManager, 'reset');
            } else {
              void showErrorMessage(
                t('error.credentialsReset'),
                Error(message)
              );
            }
          });
        }
      }
    });

    // refresh content button
    const refreshButton = new ToolbarButton({
      icon: refreshIcon,
      tooltip: t('toolbar.refresh'),
      onClick: () => {
        browser.model.refresh();
      }
    });

    // create bucket button
    const createBucketButton = new ToolbarButton({
      icon: addIcon,
      tooltip: t('toolbar.createBucket'),
      onClick: async () => {
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

    // Upload file button
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    fileInput.addEventListener('change', async () => {
      const files = fileInput.files;
      if (!files || files.length === 0) {
        return;
      }
      const currentPath = browser.model.path.replace(/^S3:/, '');
      if (!currentPath) {
        void showErrorMessage(
          t('error.upload'),
          Error(t('error.uploadNavigate'))
        );
        fileInput.value = '';
        return;
      }
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        try {
          const base64Content = await Private.readFileAsBase64(file);
          const filePath = currentPath + '/' + file.name;
          const response = await s3.uploadFile(filePath, base64Content);
          if (response.error) {
            void showErrorMessage(t('error.upload'), Error(response.message));
          }
        } catch (err: any) {
          void showErrorMessage(t('error.upload'), err);
        }
      }
      browser.model.refresh();
      fileInput.value = '';
    });

    const uploadButton = new ToolbarButton({
      icon: fileUploadIcon,
      tooltip: t('toolbar.uploadFiles'),
      onClick: () => {
        fileInput.click();
      }
    });

    // Filter toggle button + input
    const filterContainer = document.createElement('div');
    filterContainer.className = 'jp-S3Browser-filterContainer';
    filterContainer.style.display = 'none';
    const filterInput = document.createElement('input');
    filterInput.type = 'text';
    filterInput.placeholder = t('toolbar.filterPlaceholder');
    filterInput.className = 'jp-S3Browser-filterInput';
    filterContainer.appendChild(filterInput);

    filterInput.addEventListener('input', () => {
      const query = filterInput.value.toLowerCase();
      if (query) {
        (browser.model as any).setFilter((item: any) =>
          item.name.toLowerCase().includes(query)
        );
      } else {
        (browser.model as any).setFilter((item: any) => true);
      }
    });

    const filterWidget = new Widget({ node: filterContainer });

    const filterButton = new ToolbarButton({
      icon: filterListIcon,
      tooltip: t('toolbar.filterFiles'),
      onClick: () => {
        const visible = filterContainer.style.display !== 'none';
        filterContainer.style.display = visible ? 'none' : 'flex';
        if (visible) {
          filterInput.value = '';
          (browser.model as any).setFilter((item: any) => true);
        } else {
          filterInput.focus();
        }
      }
    });

    // Create folder button
    const createFolderButton = new ToolbarButton({
      icon: newFolderIcon,
      tooltip: t('toolbar.createFolder'),
      onClick: async () => {
        const currentPath = browser.model.path.replace(/^S3:/, '');
        if (!currentPath) {
          void showErrorMessage(
            t('error.createFolder'),
            Error(t('error.createFolderNavigate'))
          );
          return;
        }
        const result = await InputDialog.getText({
          title: t('dialog.createFolder'),
          label: t('dialog.folderNameLabel'),
          placeholder: t('dialog.folderNamePlaceholder')
        });
        if (result.button.accept && result.value) {
          const name = result.value.trim();
          if (!name) {
            return;
          }
          try {
            const response = await s3.createDirectory(currentPath + '/' + name);
            if ((response as any).error) {
              void showErrorMessage(
                t('error.createFolder'),
                Error((response as any).message)
              );
            } else {
              browser.model.refresh();
            }
          } catch (err: any) {
            void showErrorMessage(t('error.createFolder'), err);
          }
        }
      }
    });

    browser.toolbar.insertItem(0, 'create-bucket', createBucketButton);
    browser.toolbar.insertItem(1, 'create-folder', createFolderButton);
    browser.toolbar.insertItem(2, 'upload', uploadButton);
    browser.toolbar.insertItem(3, 'filter', filterButton);
    browser.toolbar.insertItem(10, 'filebrowser:refresh', refreshButton);
    browser.toolbar.insertItem(12, 'setting', editConfigButton);

    // Conditionally hide the reset button based on MINIO_DISABLE_RESET
    s3.getConfig()
      .then(config => {
        if (config.disable_reset) {
          editConfigButton.hide();
        }
      })
      .catch(() => {
        // Config endpoint unavailable — keep default (button visible)
      });

    // Insert filter widget between toolbar and listing
    browser.toolbar.node.parentElement?.insertBefore(
      filterWidget.node,
      browser.toolbar.node.nextSibling
    );

    /**
     * Function to handle setting credentials that are read
     * from the s3AuthenticationForm widget.
     */
    const s3AuthenticationFormSubmit = () => {
      const form = document.querySelector('#minio-form') as HTMLFormElement;
      const formData = new FormData(form);
      const formDataJSON: any = {};
      (formData as any).forEach((value: string, key: string) => {
        formDataJSON[key] = value;
      });
      const settings = ServerConnection.makeSettings();
      ServerConnection.makeRequest(
        URLExt.join(settings.baseUrl, 'jupyterlab-minio/auth'),
        {
          method: 'POST',
          body: JSON.stringify(formDataJSON)
        },
        settings
      ).then(response => {
        response.json().then(data => {
          if (data.success) {
            (this.layout as PanelLayout).removeWidget(s3AuthenticationForm);
            (this.layout as PanelLayout).addWidget(browser);
            browser.model.refresh();
            restartAllWithNotification(this._serviceManager, 'updated');
          } else {
            let errorMessage = data.message;
            if (errorMessage.includes('InvalidAccessKeyId')) {
              errorMessage = t('error.invalidAccessKey');
            } else if (errorMessage.includes('SignatureDoesNotMatch')) {
              errorMessage = t('error.invalidSecretKey');
            }
            void showErrorMessage(t('error.s3Auth'), Error(errorMessage));
          }
        });
      });
    };

    /**
     * Check if the user needs to authenticate.
     * Render the browser if they don't,
     * render the auth widget if they do.
     */
    const authStart = performance.now();
    console.log('[minio] checkIfAuthenticated START');
    Private.checkIfAuthenicated().then(result => {
      console.log(
        '[minio] checkIfAuthenticated END (%dms) authenticated=%s',
        performance.now() - authStart,
        result.authenticated
      );
      s3AuthenticationForm = new Widget({
        node: Private.createS3AuthenticationForm(s3AuthenticationFormSubmit)
      });

      if (result.authenticated) {
        (this.layout as PanelLayout).addWidget(browser);
        // not sure why this timeout is necessary
        setTimeout(() => {
          const refreshStart = performance.now();
          console.log('[minio] browser.model.refresh START');
          browser.model.refresh().then(() => {
            console.log(
              '[minio] browser.model.refresh END (%dms)',
              performance.now() - refreshStart
            );
          });
        }, 1000);
      } else {
        (this.layout as PanelLayout).addWidget(s3AuthenticationForm);
      }
    });
  }
}

namespace Private {
  /**
   * Creates an s3AuthenticationForm widget
   * @param onSubmit A function to be called when the
   * submit button is clicked.
   */
  // eslint-disable-next-line @typescript-eslint/explicit-module-boundary-types
  export function createS3AuthenticationForm(onSubmit: any): HTMLElement {
    const container = document.createElement('div');
    container.className = 'minio-form';

    // Header section
    const header = document.createElement('div');
    header.className = 'minio-form-header';

    const iconContainer = document.createElement('div');
    iconContainer.className = 'minio-form-header-icon';
    const iconEl = minioIcon.element({ height: '36px', width: '36px' });
    iconContainer.appendChild(iconEl);
    header.appendChild(iconContainer);

    const title = document.createElement('h3');
    title.className = 'minio-form-title';
    title.textContent = t('auth.title');
    header.appendChild(title);

    const description = document.createElement('p');
    description.className = 'minio-form-description';
    description.textContent = t('auth.description');
    header.appendChild(description);

    container.appendChild(header);

    // Divider
    const divider = document.createElement('hr');
    divider.className = 'minio-form-divider';
    container.appendChild(divider);

    // Form
    const form = document.createElement('form');
    form.id = 'minio-form';
    form.method = 'post';

    const fields = document.createElement('div');
    fields.className = 'minio-form-fields';

    // Endpoint URL field
    const groupUrl = document.createElement('div');
    groupUrl.className = 'minio-form-group';
    const labelUrl = document.createElement('label');
    labelUrl.className = 'minio-form-label';
    labelUrl.htmlFor = 'minio-url';
    labelUrl.textContent = t('auth.endpointUrl');
    groupUrl.appendChild(labelUrl);
    const inputUrl = document.createElement('input');
    inputUrl.className = 'minio-form-input';
    inputUrl.id = 'minio-url';
    inputUrl.type = 'url';
    inputUrl.name = 'url';
    inputUrl.placeholder = t('auth.placeholderUrl');
    groupUrl.appendChild(inputUrl);
    fields.appendChild(groupUrl);

    // Access Key ID field
    const groupAccess = document.createElement('div');
    groupAccess.className = 'minio-form-group';
    const labelAccess = document.createElement('label');
    labelAccess.className = 'minio-form-label';
    labelAccess.htmlFor = 'minio-access-key';
    labelAccess.textContent = t('auth.accessKey');
    groupAccess.appendChild(labelAccess);
    const inputAccess = document.createElement('input');
    inputAccess.className = 'minio-form-input';
    inputAccess.id = 'minio-access-key';
    inputAccess.type = 'text';
    inputAccess.name = 'accessKey';
    inputAccess.placeholder = t('auth.placeholderAccessKey');
    groupAccess.appendChild(inputAccess);
    fields.appendChild(groupAccess);

    // Secret Access Key field
    const groupSecret = document.createElement('div');
    groupSecret.className = 'minio-form-group';
    const labelSecret = document.createElement('label');
    labelSecret.className = 'minio-form-label';
    labelSecret.htmlFor = 'minio-secret-key';
    labelSecret.textContent = t('auth.secretKey');
    groupSecret.appendChild(labelSecret);
    const inputSecret = document.createElement('input');
    inputSecret.className = 'minio-form-input';
    inputSecret.id = 'minio-secret-key';
    inputSecret.type = 'password';
    inputSecret.name = 'secretKey';
    inputSecret.placeholder = t('auth.placeholderSecretKey');
    groupSecret.appendChild(inputSecret);
    fields.appendChild(groupSecret);

    form.appendChild(fields);
    container.appendChild(form);

    // Actions
    const actions = document.createElement('div');
    actions.className = 'minio-form-actions';
    const button = document.createElement('button');
    button.type = 'button';
    button.onclick = onSubmit;
    button.className = 'minio-form-button jp-mod-accept jp-mod-styled';
    button.textContent = t('auth.connect');
    actions.appendChild(button);
    container.appendChild(actions);

    return container;
  }

  /**
   * Returns true if the user is already authenticated
   * against an s3 object storage instance.
   */
  export function checkIfAuthenicated(): Promise<{
    authenticated: boolean;
  }> {
    return new Promise((resolve, reject) => {
      const settings = ServerConnection.makeSettings();
      ServerConnection.makeRequest(
        URLExt.join(settings.baseUrl, 'jupyterlab-minio/auth'),
        {
          method: 'GET'
        },
        settings
      ).then(response => {
        response.json().then(res => {
          resolve({
            authenticated: res.authenticated
          });
        });
      });
    });
  }

  /**
   * Read a File as base64 string (without the data URL prefix).
   */
  export function readFileAsBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        // Remove the "data:...;base64," prefix
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = () =>
        reject(new Error(`Failed to read file: ${file.name}`));
      reader.readAsDataURL(file);
    });
  }

  /**
   * Return true if the config file as been deleted
   */
  export function deleteConfigFile(): Promise<{
    success: boolean;
    message: string;
  }> {
    return new Promise((resolve, reject) => {
      const settings = ServerConnection.makeSettings();
      ServerConnection.makeRequest(
        URLExt.join(settings.baseUrl, 'jupyterlab-minio/auth'),
        {
          method: 'DELETE'
        },
        settings
      ).then(response => {
        response.json().then(res => {
          resolve({ success: res.success, message: res.message || '' });
        });
      });
    });
  }
}
