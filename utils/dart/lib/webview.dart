import 'dart:collection';
import 'dart:convert';
import 'package:flutter/gestures.dart';

import 'package:utils/utils.dart';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:url_launcher/url_launcher.dart';

class WebViewController {
  String? auth;
  InAppWebViewController? controller;

  setAuth(String auth) {
    this.auth = auth;
  }

  setController(InAppWebViewController controller) {
    this.controller = controller;
  }

  refresh() {
    controller?.reload();
  }

  callJS(String func, Map args) async {
    var data = {
      'func': func,
      'args': args,
    };
    String encodedData = base64.encode(utf8.encode(json.encode(data)));

    var script = '''
      window.callFromApp("$encodedData")
      ''';

    print(script);
    return await controller?.evaluateJavascript(source: script);
  }
}

class WebView extends StatefulWidget {
  final String url;
  final WebViewController controller;
  const WebView({super.key, required this.url, required this.controller});

  @override
  State<WebView> createState() => _WebViewState();
}

class _WebViewState extends State<WebView> {
  final GlobalKey webViewKey = GlobalKey();

  InAppWebViewController? webViewController;
  InAppWebViewSettings settings = InAppWebViewSettings(
      isInspectable: kDebugMode,
      mediaPlaybackRequiresUserGesture: false,
      allowsInlineMediaPlayback: true,
      iframeAllow: "camera; microphone",
      iframeAllowFullscreen: true);

  PullToRefreshController? pullToRefreshController;
  String url = "";
  double progress = 0;
  final urlController = TextEditingController();

  @override
  void initState() {
    super.initState();

    /*
    pullToRefreshController = kIsWeb
        ? null
        : PullToRefreshController(
            settings: PullToRefreshSettings(
              color: Colors.blue,
            ),
            onRefresh: () async {
              if (defaultTargetPlatform == TargetPlatform.android) {
                webViewController?.reload();
              } else if (defaultTargetPlatform == TargetPlatform.iOS) {
                webViewController?.loadUrl(
                    urlRequest:
                        URLRequest(url: await webViewController?.getUrl()));
              }
            },
          );
          */
  }

  late WebUri webUrl;
  _init() async {
    webUrl = WebUri(widget.url);
    if (widget.controller.auth != null) {
      CookieManager cookieManager = CookieManager.instance();
      await cookieManager.setCookie(
        url: webUrl,
        name: "auth",
        value: widget.controller.auth!,
        expiresDate: null,
        isSecure: true,
      );
    }
  }

  _addCallBack(InAppWebViewController controller) {
    controller.addJavaScriptHandler(
        handlerName: 'vibrate',
        callback: (args) {
          print('fuck');
          vibrate();
          //return {'bar': 'bar_value', 'baz': 'baz_value'};
        });
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Expanded(
        child: SafeArea(
            child: Column(children: <Widget>[
          Expanded(
            child: Stack(
              children: [
                FutureBuilder(
                    future: _init(),
                    builder: (context, _) {
                      return InAppWebView(
                        key: webViewKey,
                        initialUrlRequest: URLRequest(
                          url: webUrl,
                          httpShouldHandleCookies: true,
                        ),
                        initialSettings: settings,
                        gestureRecognizers: {
                          Factory<OneSequenceGestureRecognizer>(
                            () => EagerGestureRecognizer(),
                          ),
                        },
                        initialUserScripts: UnmodifiableListView<UserScript>([
                          UserScript(
                              source: "var foo = 49;",
                              injectionTime:
                                  UserScriptInjectionTime.AT_DOCUMENT_START),
                          UserScript(
                              source: "var bar = 2;",
                              injectionTime:
                                  UserScriptInjectionTime.AT_DOCUMENT_END),
                        ]),
                        onLoadStop: (controller, url) async {
                          pullToRefreshController?.endRefreshing();
                          setState(() {
                            this.url = url.toString();
                            urlController.text = this.url;
                          });
                        },
                        pullToRefreshController: pullToRefreshController,
                        onWebViewCreated: (controller) {
                          webViewController = controller;
                          widget.controller.setController(controller);
                          _addCallBack(controller);
                        },
                        onLoadStart: (controller, url) {
                          setState(() {
                            this.url = url.toString();
                            urlController.text = this.url;
                          });
                        },
                        onPermissionRequest: (controller, request) async {
                          return PermissionResponse(
                              resources: request.resources,
                              action: PermissionResponseAction.GRANT);
                        },
                        shouldOverrideUrlLoading:
                            (controller, navigationAction) async {
                          var uri = navigationAction.request.url!;

                          if (![
                            "http",
                            "https",
                            "file",
                            "chrome",
                            "data",
                            "javascript",
                            "about"
                          ].contains(uri.scheme)) {
                            if (await canLaunchUrl(uri)) {
                              // Launch the App
                              await launchUrl(
                                uri,
                              );
                              // and cancel the request
                              return NavigationActionPolicy.CANCEL;
                            }
                          }

                          return NavigationActionPolicy.ALLOW;
                        },
                        onReceivedError: (controller, request, error) {
                          pullToRefreshController?.endRefreshing();
                        },
                        onProgressChanged: (controller, progress) {
                          if (progress == 100) {
                            pullToRefreshController?.endRefreshing();
                          }
                          setState(() {
                            this.progress = progress / 100;
                            urlController.text = url;
                          });
                        },
                        onUpdateVisitedHistory:
                            (controller, url, androidIsReload) {
                          setState(() {
                            this.url = url.toString();
                            urlController.text = this.url;
                          });
                        },
                        onConsoleMessage: (controller, consoleMessage) {
                          if (kDebugMode) {
                            print(consoleMessage);
                          }
                        },
                        onReceivedServerTrustAuthRequest:
                            (controller, challenge) async {
                          return ServerTrustAuthResponse(
                              action: ServerTrustAuthResponseAction.PROCEED);
                        },
                      );
                    }),
                progress < 1.0
                    ? LinearProgressIndicator(value: progress)
                    : Container(),
              ],
            ),
          ),
        ])),
      )
    ]);
  }
}
