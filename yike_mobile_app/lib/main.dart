import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:yike_mobile_app/Pages/add_complaint.dart';
import 'package:yike_mobile_app/Pages/complaits.dart';
import 'package:yike_mobile_app/Pages/login_pge.dart';
import 'package:yike_mobile_app/Pages/splash.dart';

void main() {
  debugPaintSizeEnabled=false;
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        // This is the theme of your application.
        //
        // Try running your application with "flutter run". You'll see the
        // application has a blue toolbar. Then, without quitting the app, try
        // changing the primarySwatch below to Colors.green and then invoke
        // "hot reload" (press "r" in the console where you ran "flutter run",
        // or simply save your changes to "hotb reload" in a Flutter IDE).
        // Notice that the counter didn't reset back to zero; the application
        // is not restarted
        primarySwatch: Colors.indigo,
      ),
      home:Splash()
    );
  }
}

//

