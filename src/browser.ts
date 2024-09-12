import { PanelLayout, Widget } from "@lumino/widgets";

import { FileBrowser } from "@jupyterlab/filebrowser";

import { S3Drive } from "./contents";

import { IDocumentManager } from "@jupyterlab/docmanager";

import { h, VirtualDOM } from "@lumino/virtualdom";

import { ServerConnection } from "@jupyterlab/services";

import { URLExt } from "@jupyterlab/coreutils";

import { showErrorMessage } from "@jupyterlab/apputils";

import { ToolbarButton, showDialog, Dialog } from '@jupyterlab/apputils';

import { settingsIcon, refreshIcon } from '@jupyterlab/ui-components';

/**
 * Widget for authenticating against
 * an s3 object storage instance.
 */
let s3AuthenticationForm: any | undefined | null;

/**
 * Widget for hosting the S3 filebrowser.
 */
export class S3FileBrowser extends Widget {

  constructor(browser: FileBrowser, drive: S3Drive, manager: IDocumentManager) {
    super();
    this.addClass("jp-S3Browser");
    this.layout = new PanelLayout();

    // edit Config Button
    const editConfigButton = new ToolbarButton({
      icon: settingsIcon,
      tooltip: "Reset Your Credentials",
      onClick: async() => {
        const result = await showDialog({
          title: 'Confirmation Required',
          body: 'You have requested to reset your credentials. Before proceeding, we would like to confirm if you intended to make this request.',
          buttons: [
            Dialog.cancelButton(),
            Dialog.okButton({ label: 'Confirm' })
          ]
        });

        if (result.button.accept) {
          console.log('Configuration confirmed.');
          Private.deleteConfigFile().then(({ success, message })=> {
            if(success){
              (this.layout as PanelLayout).removeWidget(browser);
              (this.layout as PanelLayout).addWidget(s3AuthenticationForm);
            }else{
              void showErrorMessage(
                "Credentials Reset Error",
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
      tooltip: "Refresh",
      onClick: () => {
          browser.model.refresh();
      }
    });    

    // // updaload  button 
    // const uploadButton = new ToolbarButton({
    //   icon: fileUploadIcon,
    //   tooltip: "Upload",
    //   onClick: () => {
    //     // confer : https://github.com/jupyterlab/jupyterlab/blob/v3.6.8/packages/filebrowser-extension/src/index.ts#L717
    //     showDialog({
    //       title: 'Upload file',
    //       body: 'You are uploading configs',
    //       buttons: [Dialog.okButton()]
    //     });
    //   }
    // });

    browser.toolbar.insertItem(10, 'filebrowser:refresh', refreshButton);
    // browser.toolbar.insertItem(11, 'filebrowser:open-url', uploadButton);
    browser.toolbar.insertItem(12, 'setting', editConfigButton);

    
    /**
     * Function to handle setting credentials that are read
     * from the s3AuthenticationForm widget.
     */
    const s3AuthenticationFormSubmit = () => {
      const form = document.querySelector("#minio-form") as HTMLFormElement;
      const formData = new FormData(form);
      const formDataJSON: any = {};
      (formData as any).forEach((value: string, key: string) => {
        formDataJSON[key] = value;
      });
      const settings = ServerConnection.makeSettings();
      ServerConnection.makeRequest(
        URLExt.join(settings.baseUrl, "jupyterlab-minio/auth"),
        {
          method: "POST",
          body: JSON.stringify(formDataJSON),
        },
        settings
      ).then((response) => {
        response.json().then((data) => {
          if (data.success) {
            (this.layout as PanelLayout).removeWidget(s3AuthenticationForm);
            (this.layout as PanelLayout).addWidget(browser);
            browser.model.refresh();
          } else {
            let errorMessage = data.message;
            if (errorMessage.includes("InvalidAccessKeyId")) {
              errorMessage = "The access key ID you entered was invalid.";
            } else if (errorMessage.includes("SignatureDoesNotMatch")) {
              errorMessage = "The secret access key you entered was invalid";
            }
            void showErrorMessage(
              "S3 Authentication Error",
              Error(errorMessage)
            );
          }
        });
      });
    };

    /**
     * Check if the user needs to authenticate.
     * Render the browser if they don't,
     * render the auth widget if they do.
     */
    Private.checkIfAuthenicated().then((authenticated) => {
      
      s3AuthenticationForm = new Widget({
        node: Private.createS3AuthenticationForm(s3AuthenticationFormSubmit),
      });

      if (authenticated) {
        (this.layout as PanelLayout).addWidget(browser);
        // not sure why this timeout is necessary
        setTimeout(() => {
          browser.model.refresh();
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
  export function createS3AuthenticationForm(onSubmit: any): HTMLElement {
    return VirtualDOM.realize(
      h.div(
        { className: "minio-form" },
        h.h4("Minio Object Storage Browser"),
        h.div(
          "This extension allows you to browse Minio"
        ),
        h.br(),
        h.form(
          { id: "minio-form", method: "post" },
          h.p(
            h.label({}, "Endpoint URL"),
            h.br(),
            h.input({ type: "url", name: "url" })
          ),
          h.br(),
          h.p(
            h.label({}, "Access Key ID"),
            h.br(),
            h.input({ type: "text", name: "accessKey" })
          ),
          h.br(),
          h.p(
            h.label({}, "Secret Access Key"),
            h.br(),
            h.input({ type: "password", name: "secretKey" })
          ),
        ),
        h.br(),
        h.p(
          { className: "s3-connect" },
          h.button(
            {
              onclick: onSubmit,
              className: "jp-mod-accept jp-mod-styled",
            },
            "Connect"
          )
        )
      )
    );
  }

  /**
   * Returns true if the user is already authenticated
   * against an s3 object storage instance.
   */
  export function checkIfAuthenicated(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      const settings = ServerConnection.makeSettings();
      ServerConnection.makeRequest(
        URLExt.join(settings.baseUrl, "jupyterlab-minio/auth"),
        {
          method: "GET",
        },
        settings
      ).then((response) => {
        response.json().then((res) => {
          resolve(res.authenticated);
        });
      });
    });
  }

  /**
   * Return true if the config file as been deleted 
   */
  export function deleteConfigFile():Promise<{ success: boolean; message: string }>{
    return new Promise((resolve, reject) => {
      const settings = ServerConnection.makeSettings();
      ServerConnection.makeRequest(
        URLExt.join(settings.baseUrl, "jupyterlab-minio/auth"),
        {
          method: "DELETE",
        },
        settings
      ).then((response) => {
        response.json().then((res) => {
          resolve({success: res.success, message: res.message || ""});
        });
      });
    });
  }
}
