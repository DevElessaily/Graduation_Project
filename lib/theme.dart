import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class FC {
  static const deepBurgundy = Color(0xFF8B1538);
  static const darkBurgundy = Color(0xFF641027);
  static const warmWhite = Color(0xFFFFFFFF);
  static const lightGray = Color(0xFFF5F5F7);
  static const mutedGold = Color(0xFFC6A15B);
  static const darkCharcoal = Color(0xFF252525);
  static const neutralGray = Color(0xFF858585);
  static const softGreen = Color(0xFF279B70);
  static const softRed = Color(0xFFD9534F);
  static const cardShadow = Color(0x1A000000);
  static const divider = Color(0xFFE8E8EC);
  static const lightBurgundy = Color(0xFFF5E6EA);
}

TextStyle fcText(double size, FontWeight weight, Color color, {double? height, double? spacing}) =>
    TextStyle(fontSize: size, fontWeight: weight, color: color, height: height, letterSpacing: spacing);

class AppTheme {
  static ThemeData get theme => ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(seedColor: FC.deepBurgundy, surface: FC.lightGray),
    scaffoldBackgroundColor: FC.lightGray,
    textTheme: GoogleFonts.cairoTextTheme(),
    appBarTheme: const AppBarTheme(
      backgroundColor: FC.warmWhite,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: FC.darkCharcoal),
      iconTheme: IconThemeData(color: FC.deepBurgundy),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: FC.warmWhite,
      selectedItemColor: FC.deepBurgundy,
      unselectedItemColor: FC.neutralGray,
      type: BottomNavigationBarType.fixed,
      elevation: 8,
    ),
    cardTheme: CardThemeData(
      color: FC.warmWhite,
      elevation: 2,
      shadowColor: FC.cardShadow,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: FC.warmWhite,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: FC.divider)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: FC.divider)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: FC.deepBurgundy, width: 2)),
    ),
  );
}
