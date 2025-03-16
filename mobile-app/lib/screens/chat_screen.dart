import 'package:flutter/material.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class ChatScreen extends StatefulWidget {
  final String creditScore;
  final String loanAmount;
  final String loanType;
  final String language;

  const ChatScreen({
    super.key,
    required this.creditScore,
    required this.loanAmount,
    required this.loanType,
    required this.language,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<Map<String, String>> _messages = [];
  final _messageController = TextEditingController();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Ensure initial message is sent after a slight delay
    Future.delayed(Duration.zero, () {
      _sendInitialMessage();
    });
  }

  Future<void> _sendInitialMessage() async {
    setState(() {
      _isLoading = true;
    });

    // Define initial message based on selected language
    String initialMessage;
    switch (widget.language) {
      case "english":
        initialMessage =
            "My credit score is ${widget.creditScore} and I need a ${widget.loanType} loan of ${widget.loanAmount}.";
        break;
      case "hindi":
        initialMessage =
            "मेरा क्रेडिट स्कोर ${widget.creditScore} है और मुझे ${widget.loanAmount} का ${widget.loanType} लोन चाहिए।";
        break;
      case "assamese":
        initialMessage =
            "মোৰ ক্ৰেডিট স্কোৰ ${widget.creditScore} আৰু মোক ${widget.loanAmount} টকাৰ ${widget.loanType} ঋণৰ প্ৰয়োজন।";
        break;
      case "kannada":
        initialMessage =
            "ನನ್ನ ಕ್ರೆಡಿಟ್ ಸ್ಕೋರ್ ${widget.creditScore} ಮತ್ತು ನನಗೆ ${widget.loanAmount} ರೂಪಾಯಿಯ ${widget.loanType} ಸಾಲ ಬೇಕು.";
        break;
      case "tamil":
        initialMessage =
            "என் கிரெடிட் ஸ்கோர் ${widget.creditScore} மற்றும் எனக்கு ${widget.loanAmount} ரூபாய் ${widget.loanType} கடன் தேவை.";
        break;
      default:
        initialMessage =
            "My credit score is ${widget.creditScore} and I need a ${widget.loanType} loan of ${widget.loanAmount}.";
    }

    // Add the initial message to the chat
    setState(() {
      _messages.add({"sender": "user", "message": initialMessage});
    });
    await _sendMessageToBackend(initialMessage);
  }

  Future<void> _sendMessageToBackend(String message) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final response = await http.post(
        Uri.parse('http://10.72.0.119:5000/process'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "user_input": message,
          "language": widget.language,
          "credit_score": widget.creditScore,
          "loan_amount": widget.loanAmount,
          "loan_type": widget.loanType,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['response'] != null) {
          setState(() {
            _messages.add({"sender": "bot", "message": data['response']});
            _isLoading = false;
          });
        } else {
          setState(() {
            _messages.add({"sender": "bot", "message": "Error: No response from server."});
            _isLoading = false;
          });
        }
      } else {
        setState(() {
          _messages.add({
            "sender": "bot",
            "message": "Error: Server responded with status ${response.statusCode}"
          });
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _messages.add({"sender": "bot", "message": "Error: Failed to connect to server. $e"});
        _isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          "Chat with Loan Buddy",
          style: GoogleFonts.poppins(color: Colors.white),
        ),
        backgroundColor: Theme.of(context).primaryColor,
      ),
      body: Container(
        color: Theme.of(context).brightness == Brightness.dark
            ? Colors.grey[900]
            : Colors.white,
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(10),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final message = _messages[index];
                  final isUser = message["sender"] == "user";
                  return Align(
                    alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: isUser
                            ? Theme.of(context).primaryColor
                            : Colors.grey[600],
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        message["message"]!,
                        style: GoogleFonts.poppins(
                          color: isUser ? Colors.white : Colors.black, // Changed to black for bot messages
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            if (_isLoading)
              Padding(
                padding: const EdgeInsets.all(10),
                child: SpinKitThreeBounce(
                  color: Theme.of(context).primaryColor,
                  size: 20,
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(10),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _messageController,
                      decoration: InputDecoration(
                        hintText: "Type your message...",
                        hintStyle: GoogleFonts.poppins(),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  IconButton(
                    onPressed: () {
                      if (_messageController.text.isNotEmpty) {
                        setState(() {
                          _messages.add({"sender": "user", "message": _messageController.text});
                        });
                        _sendMessageToBackend(_messageController.text);
                        _messageController.clear();
                      }
                    },
                    icon: Icon(
                      Icons.send,
                      color: Theme.of(context).primaryColor,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
