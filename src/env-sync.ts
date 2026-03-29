/**
 * Kernel and terminal restart helpers.
 *
 * After MinIO credentials are set or reset, these functions restart
 * all running kernels and terminals so they pick up the new
 * environment variables (via IPython/shell startup hooks).
 */

import { ServiceManager } from '@jupyterlab/services';
import { Notification } from '@jupyterlab/apputils';
import { t } from './i18n';

/**
 * Restart all running kernels so they re-execute the
 * IPython startup hook and pick up new MinIO env vars.
 */
export async function restartAllKernels(
  serviceManager: ServiceManager.IManager
): Promise<void> {
  await serviceManager.sessions.refreshRunning();
  const sessions = [...serviceManager.sessions.running()];
  if (sessions.length === 0) {
    return;
  }
  for (const session of sessions) {
    try {
      const connection = serviceManager.sessions.connectTo({
        model: session
      });
      if (connection.kernel) {
        await connection.kernel.restart();
      }
      connection.dispose();
    } catch (e) {
      console.warn(
        '[minio] Failed to restart kernel for session',
        session.id,
        e
      );
    }
  }
}

/**
 * Restart all running terminals by shutting them down and
 * starting new ones. New terminals inherit the server's
 * updated os.environ and also source the shell startup hook.
 */
export async function restartAllTerminals(
  serviceManager: ServiceManager.IManager
): Promise<void> {
  if (!serviceManager.terminals.isAvailable()) {
    return;
  }
  await serviceManager.terminals.refreshRunning();
  const terminals = [...serviceManager.terminals.running()];
  if (terminals.length === 0) {
    return;
  }
  for (const terminal of terminals) {
    try {
      await serviceManager.terminals.shutdown(terminal.name);
    } catch (e) {
      console.warn('[minio] Failed to shut down terminal', terminal.name, e);
    }
  }
  // Start the same number of fresh terminals
  for (let i = 0; i < terminals.length; i++) {
    try {
      await serviceManager.terminals.startNew();
    } catch (e) {
      console.warn('[minio] Failed to start new terminal', e);
    }
  }
}

/**
 * Restart all kernels and terminals, showing a notification.
 */
export async function restartAllWithNotification(
  serviceManager: ServiceManager.IManager,
  reason: 'updated' | 'reset'
): Promise<void> {
  const message =
    reason === 'updated'
      ? t('notification.credentialsUpdated')
      : t('notification.credentialsReset');

  Notification.info(message, { autoClose: 5000 });

  await restartAllKernels(serviceManager);
  await restartAllTerminals(serviceManager);
}
