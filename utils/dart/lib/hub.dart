import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:fetch_client/fetch_client.dart';
import 'package:encrypt/encrypt.dart' as encrypt;

import 'package:flutter_client_sse/constants/sse_request_type_enum.dart';
import 'package:flutter_client_sse/flutter_client_sse.dart';
import 'dart:async';
import './utils.dart';

class Encrypotion {
  final keyString = 'abc10086abc10086';
  late encrypt.Encrypter encrypter;
  late encrypt.IV iv;

  Encrypotion() {
    final key = encrypt.Key.fromUtf8(keyString);
    encrypter = encrypt.Encrypter(encrypt.AES(key, mode: encrypt.AESMode.ecb));
    iv = encrypt.IV.fromLength(16);
  }

  String enc(String plainText) {
    final encrypted = encrypter.encrypt(plainText, iv: iv);

    return encrypted.base64;
  }

  String dec(String encText) {
    encText = encText.replaceAll('\n', '').replaceAll(' ', '');
    final encrypted = encrypt.Encrypted.fromBase64(encText);
    final decrypted = encrypter.decrypt(encrypted, iv: iv);

    return decrypted;
  }
}

Future callRemote(
    {required String clsName,
    required String funcName,
    required Map<String, dynamic> args,
    required String remoteUrl}) async {
  var url = Uri.parse('$remoteUrl/call');
  var encodedData = jsonEncode({
    'cls_name': clsName,
    'init_args': {},
    'func_name': funcName,
    'func_args': args
  });

  http.Client? client;
  try {
    if (!Platform.isFuchsia) {
      client = http.Client();
    }
  } catch (e) {
    client = FetchClient(mode: RequestMode.cors);
  }
  var res = await client!.post(url,
      headers: {'Content-Type': 'application/json'}, body: encodedData);
  var data = jsonDecode(res.body);
  return data;
}

Stream streamRemote(
    {required String clsName,
    required String funcName,
    required Map<String, dynamic> args,
    required String remoteUrl}) async* {
  var url = Uri.parse('$remoteUrl/stream');
  var encodedData = jsonEncode({
    'cls_name': clsName,
    'init_args': {},
    'func_name': funcName,
    'func_args': args
  });

  http.Client? client;
  try {
    if (!Platform.isFuchsia) {
      client = http.Client();
    }
  } catch (e) {
    client = FetchClient(mode: RequestMode.cors);
  }

  final stream = await client!.send(http.Request(
    'POST',
    url,
  )
    ..headers['Content-Type'] = 'application/json'
    ..body = encodedData);

  var data = '';
  await for (final bytes in stream.stream) {
    data += utf8.decode(bytes);
    if (data.endsWith('\n')) {
      final res = jsonDecode(data);
      data = '';
      var prop = States().getProperty(res['name']);
      if (prop == null) {
        prop = Property(
            name: res['name'], defaultValue: res['data'], setState: () {});
        States().statesDict[res['name']] = prop;
      } else {
        prop.value = res['data'];
      }
      yield res;
    }

    //final data = jsonDecode(utf8.decode(bytes));
    //States().getProperty(data['name'])?.value = data['data'];
    //print('Response data: $data');
    //yield data;
  }
}

class Property<T> {
  final String name;
  final T defaultValue;
  final Function? setState;
  var setStates = <Function>{};
  Property(
      {required this.name,
      required this.defaultValue,
      required this.setState}) {
    if (setState != null) {
      setStates.add(setState!);
    }
  }

  T? _value;

  T get value => _value ?? defaultValue;

  set value(T newValue) {
    _value = newValue;
    update();
  }

  update() {
    print('update $name ${setStates.length}');
    for (var setState in setStates) {
      setState();
    }
  }

  destroy() {
    States().statesDict.remove(name);
  }

  addRefrshFunc(Function refreshFunc) {
    setStates.add(refreshFunc);
  }

  removeRefreshFunc(Function refreshFunc) {
    setStates.remove(refreshFunc);
  }
}

class States {
  // Create a stream controller
  static final _instance = States._internal();

  factory States() {
    return _instance;
  }

  States._internal();

  var statesDict = <String, Property>{};

  Property? getProperty(String name) {
    return statesDict[name];
  }
}

class SSEListener {
  static SSEListener? _instance;
  final states = States();
  String? remoteUrl;

  factory SSEListener(remoteUrl) {
    if (SSEListener._instance == null) {
      _instance = SSEListener._internal(remoteUrl);
    }
    return _instance!;
  }

  SSEListener._internal(this.remoteUrl) {
    try {
      SSEClient.unsubscribeFromSSE();
    } catch (e) {
      print(e);
    }
    //subscibeToRemote();
  }

  Stream? sse;
  StreamSubscription? sseSub;

  subscibeToRemote() {
    print('--------subscibe sse');
    sse = SSEClient.subscribeToSSE(
        method: SSERequestType.GET,
        url: '$remoteUrl/listen/test_channel',
        header: {
          "Accept": "text/event-stream",
          "Cache-Control": "no-cache",
        });
    sseSub = sse?.listen(
      (event) {
        if (event.event != 'update') {
          print('unhandle sse event: ${event.event}');
          return;
        }
        print('recevie ${event.data?.length}');
        Map state;
        String decText = '';
        try {
          //decText = Encrypotion().dec(event.data!);
          //state = jsonDecode(decText);
          state = jsonDecode(event.data);
        } catch (e) {
          print('decode error');
          print(e);
          //print(event.data);
          print(decText);
          return;
        }
        if (event.data != null) {
          var prop = States().getProperty(state['name']);
          if (prop != null) {
            print("remote state receive ${state['name']}");
            prop.value = state['data'];
          } else {
            print("remote state miss target ${state['name']}");
          }
        }
      },
      onError: (e) {
        print('sse error');
        print(e);
        Future.delayed(const Duration(seconds: 2)).then((e) {
          print('reconnect');
          subscibeToRemote();
        });
      },
      onDone: () {
        print('sse done');
      },
    );
  }

  dispose() {
    //sseSub.cancel();
    //SSEClient.unsubscribeFromSSE();
  }
}
