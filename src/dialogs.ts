import { Widget } from '@lumino/widgets';

import { Dialog, showDialog, InputDialog } from '@jupyterlab/apputils';

import * as s3 from './s3';

/**
 * A widget that provides an S3 path picker with navigation.
 */
class S3PathPickerWidget extends Widget {
  private _pathInput: HTMLInputElement;
  private _listContainer: HTMLDivElement;
  private _currentPath: string;

  constructor(initialPath: string) {
    super();
    this._currentPath = initialPath || '';

    const container = document.createElement('div');
    container.className = 'minio-path-picker';

    // Path input
    const label = document.createElement('label');
    label.textContent = 'S3 Path:';
    container.appendChild(label);

    this._pathInput = document.createElement('input');
    this._pathInput.type = 'text';
    this._pathInput.value = this._currentPath;
    this._pathInput.className = 'jp-mod-styled minio-path-input';
    this._pathInput.style.width = '100%';
    this._pathInput.style.marginBottom = '8px';
    this._pathInput.style.boxSizing = 'border-box';
    container.appendChild(this._pathInput);

    // Navigation list
    this._listContainer = document.createElement('div');
    this._listContainer.className = 'minio-path-list';
    this._listContainer.style.border = '1px solid var(--jp-border-color1)';
    this._listContainer.style.height = '200px';
    this._listContainer.style.overflowY = 'auto';
    this._listContainer.style.padding = '4px';
    container.appendChild(this._listContainer);

    this.node.appendChild(container);

    // Load initial listing
    this._loadPath(this._currentPath);
  }

  getValue(): string {
    return this._pathInput.value.trim();
  }

  private async _loadPath(path: string): Promise<void> {
    this._currentPath = path;
    this._pathInput.value = path;
    this._listContainer.innerHTML = '';

    try {
      const result = await s3.ls(path);
      const items: any[] = result.content || [];

      // Add parent navigation if not at root
      if (path !== '') {
        const parentItem = document.createElement('div');
        parentItem.textContent = '.. (parent)';
        parentItem.style.cursor = 'pointer';
        parentItem.style.padding = '4px 8px';
        parentItem.style.fontStyle = 'italic';
        parentItem.addEventListener('mouseenter', () => {
          parentItem.style.backgroundColor = 'var(--jp-layout-color2)';
        });
        parentItem.addEventListener('mouseleave', () => {
          parentItem.style.backgroundColor = '';
        });
        parentItem.addEventListener('click', () => {
          const parts = path.replace(/\/$/, '').split('/');
          parts.pop();
          this._loadPath(parts.join('/'));
        });
        this._listContainer.appendChild(parentItem);
      }

      for (const item of items) {
        if (item.type === 'directory') {
          const el = document.createElement('div');
          el.textContent = item.name + '/';
          el.style.cursor = 'pointer';
          el.style.padding = '4px 8px';
          el.addEventListener('mouseenter', () => {
            el.style.backgroundColor = 'var(--jp-layout-color2)';
          });
          el.addEventListener('mouseleave', () => {
            el.style.backgroundColor = '';
          });
          el.addEventListener('click', () => {
            const newPath = item.path.replace(/\/$/, '');
            this._loadPath(newPath);
          });
          this._listContainer.appendChild(el);
        }
      }

      if (
        items.filter(i => i.type === 'directory').length === 0 &&
        path !== ''
      ) {
        const empty = document.createElement('div');
        empty.textContent = '(no subdirectories)';
        empty.style.padding = '4px 8px';
        empty.style.fontStyle = 'italic';
        empty.style.color = 'var(--jp-ui-font-color2)';
        this._listContainer.appendChild(empty);
      }
    } catch (err) {
      const errEl = document.createElement('div');
      errEl.textContent = 'Error loading path';
      errEl.style.color = 'var(--jp-error-color1)';
      this._listContainer.appendChild(errEl);
    }
  }
}

/**
 * Show a dialog for picking an S3 path (bucket/directory).
 */
export async function showS3PathPickerDialog(
  title: string,
  currentPath: string
): Promise<string | null> {
  const picker = new S3PathPickerWidget(currentPath);

  const result = await showDialog({
    title,
    body: picker,
    buttons: [Dialog.cancelButton(), Dialog.okButton({ label: 'Select' })]
  });

  if (result.button.accept) {
    return picker.getValue();
  }
  return null;
}

/**
 * Show a dialog for entering a local filesystem path.
 */
export async function showLocalPathInputDialog(
  title: string,
  defaultPath: string
): Promise<string | null> {
  const result = await InputDialog.getText({
    title,
    label: 'Local path (relative to Jupyter root):',
    placeholder: defaultPath || 'path/to/file.txt'
  });

  if (result.button.accept && result.value) {
    return result.value.trim();
  }
  return null;
}
