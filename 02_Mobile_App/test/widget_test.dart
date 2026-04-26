import 'package:flutter_test/flutter_test.dart';
import 'package:puf_authenticator/main.dart';

void main() {
  testWidgets('App starts correctly', (WidgetTester tester) async {
    await tester.pumpWidget(const PufAuthApp());
    expect(find.text('PUF Authenticator'), findsOneWidget);
  });
}
