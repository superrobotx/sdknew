library utils;

import 'package:permission_handler/permission_handler.dart';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:vibration/vibration.dart';
import 'package:shared_preferences/shared_preferences.dart';

print(Object? s) {
  debugPrint('chat: $s');
}

Future<File> getTemporaryFile(ext) async {
  final directory = await getTemporaryDirectory();
  final file = File('${directory.path}/temp_file.$ext');
  return file;
}

vibrate({int dur = 600}) async {
  if (await Vibration.hasCustomVibrationsSupport() ?? false) {
    Vibration.vibrate(duration: dur);
    print('vibrate');
  } else {
    print('vibrate no support');
  }
}

class Cache {
  static final Cache _singleton = Cache._internal();

  factory Cache() {
    return _singleton;
  }
  SharedPreferences? pref;

  Cache._internal();

  init() async {
    pref ??= await SharedPreferences.getInstance();
  }

  set(key, value) async {
    return await pref?.setString(key, jsonEncode(value));
  }

  get(key) {
    var value = pref?.getString(key);
    if (value != null) {
      return jsonDecode(value);
    }
  }

  clear() async {
    await pref?.clear();
  }
}

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
