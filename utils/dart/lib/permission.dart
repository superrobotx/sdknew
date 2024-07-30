import 'package:permission_handler/permission_handler.dart';
import './utils.dart';

getPermission(Permission permission) async {
  if (!(await permission.request().isGranted)) {
    PermissionStatus status = await Permission.storage.request();
    if (status.isGranted) {
      print('get ${permission.toString()} permission success');
    } else {
      // Permission denied.
      if (status.isPermanentlyDenied) {
        // User denied permission permanently, navigate to app settings.
        await openAppSettings();
      }
    }
  }
}
