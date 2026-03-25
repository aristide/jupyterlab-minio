/**
 * Lightweight i18n module for jupyterlab-minio.
 * Supports English (default) and French.
 */

const translations: Record<string, Record<string, string>> = {
  en: {
    // Auth form
    'auth.title': 'MinIO Object Storage',
    'auth.description':
      'Connect to your MinIO instance to browse and manage objects.',
    'auth.endpointUrl': 'Endpoint URL',
    'auth.accessKey': 'Access Key ID',
    'auth.secretKey': 'Secret Access Key',
    'auth.connect': 'Connect',
    'auth.placeholderUrl': 'https://play.min.io',
    'auth.placeholderAccessKey': 'Enter your access key',
    'auth.placeholderSecretKey': 'Enter your secret key',

    // Sidebar
    'sidebar.caption': 'Minio Browser',

    // Toolbar tooltips
    'toolbar.resetCredentials': 'Reset Your Credentials',
    'toolbar.refresh': 'Refresh',
    'toolbar.createBucket': 'Create Bucket',
    'toolbar.uploadFiles': 'Upload Files',
    'toolbar.filterFiles': 'Filter Files',
    'toolbar.createFolder': 'Create Folder',
    'toolbar.filterPlaceholder': 'Filter files...',

    // Dialogs
    'dialog.confirmRequired': 'Confirmation Required',
    'dialog.confirmResetBody':
      'You have requested to reset your credentials. Before proceeding, we would like to confirm if you intended to make this request.',
    'dialog.confirm': 'Confirm',
    'dialog.createBucket': 'Create New Bucket',
    'dialog.bucketNameLabel':
      'Bucket name (lowercase, 3-63 chars, alphanumeric and hyphens):',
    'dialog.bucketNamePlaceholder': 'my-bucket-name',
    'dialog.createFolder': 'Create New Folder',
    'dialog.folderNameLabel': 'Folder name:',
    'dialog.folderNamePlaceholder': 'my-folder',
    'dialog.deleteFromS3': 'Delete from S3',
    'dialog.deleteConfirm': 'Are you sure you want to delete:',
    'dialog.s3Path': 'S3 Path:',
    'dialog.parentDir': '.. (parent)',
    'dialog.noSubdirectories': '(no subdirectories)',
    'dialog.select': 'Select',
    'dialog.localPathLabel': 'Local path (relative to Jupyter root):',
    'dialog.copyToS3Path': 'Copy to S3 Path',
    'dialog.moveToS3Path': 'Move to S3 Path',
    'dialog.copyS3ToLocal': 'Copy S3 File to Local',
    'dialog.copyLocalToS3': 'Copy Local File to S3',

    // Command labels
    'command.createBucket': 'Create Bucket',
    'command.deleteBucket': 'Delete Bucket',
    'command.copyToPath': 'Copy to S3 Path...',
    'command.moveToPath': 'Move to S3 Path...',
    'command.copyToLocal': 'Copy to Local Filesystem...',
    'command.copyToS3': 'Copy to S3...',
    'command.deleteFromS3': 'Delete from S3',

    // Error messages
    'error.credentialsReset': 'Credentials Reset Error',
    'error.bucketCreation': 'Bucket Creation Error',
    'error.bucketDeletion': 'Bucket Deletion Error',
    'error.upload': 'Upload Error',
    'error.uploadNavigate':
      'Please navigate into a bucket before uploading files.',
    'error.createFolder': 'Create Folder Error',
    'error.createFolderNavigate':
      'Please navigate into a bucket before creating a folder.',
    'error.s3Auth': 'S3 Authentication Error',
    'error.invalidAccessKey': 'The access key ID you entered was invalid.',
    'error.invalidSecretKey':
      'The secret access key you entered was invalid.',
    'error.copy': 'Copy Error',
    'error.move': 'Move Error',
    'error.transfer': 'Transfer Error',
    'error.delete': 'Delete Error',
    'error.deleteFailed': 'Failed to delete',
    'error.loadingPath': 'Error loading path'
  },
  fr: {
    // Auth form
    'auth.title': 'Stockage Objet MinIO',
    'auth.description':
      'Connectez-vous a votre instance MinIO pour parcourir et gerer vos objets.',
    'auth.endpointUrl': 'URL du point d\'acces',
    'auth.accessKey': 'Identifiant de cle d\'acces',
    'auth.secretKey': 'Cle d\'acces secrete',
    'auth.connect': 'Se connecter',
    'auth.placeholderUrl': 'https://play.min.io',
    'auth.placeholderAccessKey': 'Entrez votre cle d\'acces',
    'auth.placeholderSecretKey': 'Entrez votre cle secrete',

    // Sidebar
    'sidebar.caption': 'Explorateur MinIO',

    // Toolbar tooltips
    'toolbar.resetCredentials': 'Reinitialiser vos identifiants',
    'toolbar.refresh': 'Actualiser',
    'toolbar.createBucket': 'Creer un compartiment',
    'toolbar.uploadFiles': 'Telecharger des fichiers',
    'toolbar.filterFiles': 'Filtrer les fichiers',
    'toolbar.createFolder': 'Creer un dossier',
    'toolbar.filterPlaceholder': 'Filtrer les fichiers...',

    // Dialogs
    'dialog.confirmRequired': 'Confirmation requise',
    'dialog.confirmResetBody':
      'Vous avez demande la reinitialisation de vos identifiants. Avant de continuer, nous souhaitons confirmer que vous avez bien fait cette demande.',
    'dialog.confirm': 'Confirmer',
    'dialog.createBucket': 'Creer un nouveau compartiment',
    'dialog.bucketNameLabel':
      'Nom du compartiment (minuscules, 3-63 car., alphanumerique et tirets) :',
    'dialog.bucketNamePlaceholder': 'mon-compartiment',
    'dialog.createFolder': 'Creer un nouveau dossier',
    'dialog.folderNameLabel': 'Nom du dossier :',
    'dialog.folderNamePlaceholder': 'mon-dossier',
    'dialog.deleteFromS3': 'Supprimer de S3',
    'dialog.deleteConfirm':
      'Etes-vous sur de vouloir supprimer :',
    'dialog.s3Path': 'Chemin S3 :',
    'dialog.parentDir': '.. (parent)',
    'dialog.noSubdirectories': '(aucun sous-repertoire)',
    'dialog.select': 'Selectionner',
    'dialog.localPathLabel':
      'Chemin local (relatif a la racine Jupyter) :',
    'dialog.copyToS3Path': 'Copier vers un chemin S3',
    'dialog.moveToS3Path': 'Deplacer vers un chemin S3',
    'dialog.copyS3ToLocal': 'Copier un fichier S3 en local',
    'dialog.copyLocalToS3': 'Copier un fichier local vers S3',

    // Command labels
    'command.createBucket': 'Creer un compartiment',
    'command.deleteBucket': 'Supprimer le compartiment',
    'command.copyToPath': 'Copier vers un chemin S3...',
    'command.moveToPath': 'Deplacer vers un chemin S3...',
    'command.copyToLocal': 'Copier vers le systeme local...',
    'command.copyToS3': 'Copier vers S3...',
    'command.deleteFromS3': 'Supprimer de S3',

    // Error messages
    'error.credentialsReset':
      'Erreur de reinitialisation des identifiants',
    'error.bucketCreation': 'Erreur de creation du compartiment',
    'error.bucketDeletion': 'Erreur de suppression du compartiment',
    'error.upload': 'Erreur de telechargement',
    'error.uploadNavigate':
      'Veuillez naviguer dans un compartiment avant de telecharger des fichiers.',
    'error.createFolder': 'Erreur de creation du dossier',
    'error.createFolderNavigate':
      'Veuillez naviguer dans un compartiment avant de creer un dossier.',
    'error.s3Auth': 'Erreur d\'authentification S3',
    'error.invalidAccessKey':
      'L\'identifiant de cle d\'acces saisi est invalide.',
    'error.invalidSecretKey':
      'La cle d\'acces secrete saisie est invalide.',
    'error.copy': 'Erreur de copie',
    'error.move': 'Erreur de deplacement',
    'error.transfer': 'Erreur de transfert',
    'error.delete': 'Erreur de suppression',
    'error.deleteFailed': 'Echec de la suppression de',
    'error.loadingPath': 'Erreur de chargement du chemin'
  }
};

let currentLocale = 'en';

/**
 * Get a translated string by key.
 * Falls back to English, then to the raw key.
 */
export function t(key: string): string {
  const locale = translations[currentLocale];
  if (locale && locale[key] !== undefined) {
    return locale[key];
  }
  const en = translations['en'];
  if (en && en[key] !== undefined) {
    return en[key];
  }
  return key;
}

/**
 * Set the active locale.
 */
export function setLocale(locale: string): void {
  currentLocale = locale;
}
