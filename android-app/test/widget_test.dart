import 'package:flutter_test/flutter_test.dart';

import 'package:android_capture/main.dart';

void main() {
  testWidgets('App builds', (WidgetTester tester) async {
    await tester.pumpWidget(const ParentalMonitorApp());
    expect(find.textContaining('User ID'), findsOneWidget);
  });
}
