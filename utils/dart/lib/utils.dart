library utils;

import 'package:audioplayers/audioplayers.dart';
import 'package:permission_handler/permission_handler.dart';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:vibration/vibration.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:toastification/toastification.dart';

print(Object? s) {
  debugPrint('chat: $s');
}

showToast(msg, {seconds = 2}) {
  toastification.show(
    title: Text(msg),
    autoCloseDuration: Duration(seconds: seconds),
  );
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

  dynamic? get(key) {
    var value = pref?.getString(key);
    if (value != null) {
      return jsonDecode(value);
    }
    return null;
  }

  containerKey(key) {
    return pref?.containsKey(key);
  }

  Future<void> clear() async {
    await pref?.clear();
  }

  List<String>? listKeys() {
    return pref?.getKeys().toList().cast<String>();
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

class Sound {
  static final Sound _instance = Sound._internal();

  factory Sound() {
    return _instance;
  }

  Sound._internal();

  AudioPlayer player = AudioPlayer();

  void play(String soundPath, {volume = 1.0}) async {
    if (player.state == PlayerState.playing) {
      await player.stop();
    }
    await player.play(AssetSource(soundPath), volume: volume);
  }
}

String generateRandomString({length = 16}) {
  final random = Random();

  String generateRandomString(int length) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    return String.fromCharCodes(
      List.generate(
          length, (_) => chars.codeUnitAt(random.nextInt(chars.length))),
    );
  }

  final randomString = generateRandomString(length);
  return randomString;
}
