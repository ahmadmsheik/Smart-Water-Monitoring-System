import 'dart:async';
import 'package:http/http.dart' as http;
import '../api_config.dart';

class StreamService {
  StreamController<double>? _controller;
  http.Client? _client;

  Stream<double> streamFlowRate(int sensorId) {
    _controller = StreamController<double>.broadcast(
      onListen: () => _startListening(sensorId),
      onCancel: () => _stopListening(),
    );
    return _controller!.stream;
  }

  // void _startListening(int sensorId) {
  //   _client = http.Client();
  //   var request = http.Request('GET', Uri.parse('$_baseUrl/stream/$sensorId'));
  //   request.headers['Cache-Control'] = 'no-cache';
  //   request.headers['Accept'] = 'text/event-stream';

  //   _client!.send(request).then((response) {
  //     response.stream.transform(StreamTransformer.fromHandlers(
  //       handleData: (data, sink) {
  //         String eventData = String.fromCharCodes(data);
  //         if (eventData.startsWith('data:')) {
  //           String flowRateStr = eventData.substring(5).trim();
  //           try {
  //             double flowRate = double.parse(flowRateStr);
  //             sink.add(flowRate);
  //           } catch (e) {
  //             print('Error parsing flow rate: $e');
  //           }
  //         }
  //       },
  //     )).listen(
  //       (dynamic flowRate) => _controller?.add(flowRate as double),
  //       onError: (error) => _controller?.addError(error),
  //     );
  //   });
  // }

  void _startListening(int sensorId) {
    print('[FLUTTER] Connecting to /stream/$sensorId');
    _client = http.Client();
    var request = http.Request('GET', apiUri('stream/$sensorId'));
    request.headers['Cache-Control'] = 'no-cache';
    request.headers['Accept'] = 'text/event-stream';

    _client!.send(request).then((response) {
      print(
          '[FLUTTER] Connected to /stream/$sensorId, status = ${response.statusCode}');

      response.stream.transform(StreamTransformer.fromHandlers(
        handleData: (data, sink) {
          String eventData = String.fromCharCodes(data);
          print('[FLUTTER] Raw event for sensor $sensorId: $eventData');

          if (eventData.startsWith('data:')) {
            String flowRateStr = eventData.substring(5).trim();
            try {
              double flowRate = double.parse(flowRateStr);
              print(
                  '[FLUTTER] Parsed flowRate = $flowRate for sensor $sensorId');
              sink.add(flowRate);
            } catch (e) {
              print(
                  '[FLUTTER ERROR] Failed to parse flow rate for sensor $sensorId: $e');
            }
          }
        },
      )).listen(
        (dynamic flowRate) => _controller?.add(flowRate as double),
        onError: (error) =>
            print('[FLUTTER ERROR] Stream error for sensor $sensorId: $error'),
      );
    }).catchError((e) {
      print('[FLUTTER ERROR] Connection error for sensor $sensorId: $e');
    });
  }

  void _stopListening() {
    _client?.close();
    _client = null;

    if (_controller != null && !_controller!.isClosed) {
      _controller!.close();
    }
    _controller = null;
  }

  void dispose() {
    _stopListening();
  }
}
