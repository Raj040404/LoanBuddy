package main
 
 import (
     "bytes"
     "context"
     "encoding/json"
     "io"
     "log"
     "net/http"
     "os"
     "os/signal"
     "time"
 
     "go.mau.fi/whatsmeow"
     "go.mau.fi/whatsmeow/store/sqlstore"
     "go.mau.fi/whatsmeow/types/events"
     "go.mau.fi/whatsmeow/types"
     whatsappProto "go.mau.fi/whatsmeow/binary/proto"
     _ "github.com/mattn/go-sqlite3"
 )
 
 var client *whatsmeow.Client
 
 func main() {
     log.Println("Starting WhatsMeow service...")
 
     db, err := sqlstore.New("sqlite3", "file:whatsapp_session.db?_foreign_keys=on", nil)
     if err != nil {
         log.Fatalf("Failed to setup database: %v", err)
     }
     log.Println("Database initialized.")
 
     deviceStore, err := db.GetFirstDevice()
     if err != nil {
         log.Fatalf("Failed to get device: %v", err)
     }
     log.Println("Device store loaded.")
 
     client = whatsmeow.NewClient(deviceStore, nil)
     client.AddEventHandler(eventHandler)
     log.Println("Client initialized.")
 
     if client.Store.ID == nil {
         log.Println("No session found, generating QR code...")
         qrChan, _ := client.GetQRChannel(context.Background())
         err = client.Connect()
         if err != nil {
             log.Fatalf("Failed to connect: %v", err)
         }
         for evt := range qrChan {
             if evt.Event == "code" {
                 log.Println("Scan this QR code with WhatsApp:", evt.Code)
             } else {
                 log.Println("Login event:", evt.Event)
             }
         }
     } else {
         log.Println("Existing session found, connecting...")
         err = client.Connect()
         if err != nil {
             log.Fatalf("Failed to connect: %v", err)
         }
         log.Println("Connected successfully!")
     }
 
     http.HandleFunc("/send", sendMessageHandler)
     go func() {
         log.Println("Starting HTTP server on :8080")
         log.Fatal(http.ListenAndServe(":8080", nil))
     }()
 
     log.Println("Service running. Press Ctrl+C to exit.")
     c := make(chan os.Signal, 1)
     signal.Notify(c, os.Interrupt)
     <-c
     log.Println("Shutting down...")
     client.Disconnect()
 }
 
 func eventHandler(evt interface{}) {
     switch v := evt.(type) {
     case *events.Message:
         if v.Info.IsFromMe { // Ignore messages sent by this client
             return
         }
         log.Printf("Received message from %s: %s", v.Info.Sender.String(), v.Message.GetConversation())
         // Forward to Python
         msg := struct {
             From    string `json:"from"`
             Message string `json:"message"`
         }{
             From:    v.Info.Sender.String(),
             Message: v.Message.GetConversation(),
         }
         payload, _ := json.Marshal(msg)
         resp, err := http.Post("http://localhost:5000/incoming", "application/json", bytes.NewBuffer(payload))
         if err != nil {
             log.Printf("Failed to forward to Python: %v", err)
         } else {
             resp.Body.Close()
             log.Println("Message forwarded to Python")
         }
 
         // Handle voice messages
         if v.Message.AudioMessage != nil || v.Message.Ptt != nil {
             log.Println("Voice message detected, downloading...")
             msgID := v.Info.ID
             data, err := client.Download(v.Message)
             if err != nil {
                 log.Printf("Failed to download voice message: %v", err)
                 return
             }
             audioFile := "user_input.wav"
             err = os.WriteFile(audioFile, data, 0644)
             if err != nil {
                 log.Printf("Failed to save audio: %v", err)
                 return
             }
             voiceMsg := struct {
                 From    string `json:"from"`
                 Message string `json:"message"`
                 Type    string `json:"type"`
             }{
                 From:    v.Info.Sender.String(),
                 Message: audioFile,
                 Type:    "voice",
             }
             voicePayload, _ := json.Marshal(voiceMsg)
             resp, err = http.Post("http://localhost:5000/incoming", "application/json", bytes.NewBuffer(voicePayload))
             if err != nil {
                 log.Printf("Failed to forward voice to Python: %v", err)
             } else {
                 resp.Body.Close()
                 log.Println("Voice message forwarded to Python")
             }
             os.Remove(audioFile) // Clean up
         }
     }
 }
 
 func sendMessageHandler(w http.ResponseWriter, r *http.Request) {
     var req struct {
         To        string `json:"to"`
         Message   string `json:"message"`
         MediaPath string `json:"media_path,omitempty"`
     }
     if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
         log.Println("Invalid request:", err)
         http.Error(w, "Invalid request", http.StatusBadRequest)
         return
     }
 
     jid, err := types.ParseJID(req.To)
     if err != nil {
         log.Println("Invalid JID:", err)
         http.Error(w, "Invalid JID", http.StatusBadRequest)
         return
     }
 
     msg := &whatsappProto.Message{Conversation: &req.Message}
     if req.MediaPath != "" && os.path.exists(req.MediaPath) {
         file, err := os.Open(req.MediaPath)
         if err != nil {
             log.Println("Failed to open media file:", err)
             http.Error(w, "Failed to open media file", http.StatusInternalServerError)
             return
         }
         defer file.Close()
         msg.AudioMessage = &whatsappProto.AudioMessage{
             Url:         &req.MediaPath,
             MimType:     proto.String("audio/wav"),
             FileEncSha256: []byte{},
             FileSha256:   []byte{},
             FileLength:   proto.Uint64(uint64(file.Stat().Size())),
         }
         // Note: WhatsMeow requires proper media upload handling; this is a simplified version.
         // For full media support, use client.Upload() and set msg appropriately.
     }
 
     ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
     defer cancel()
     _, err = client.SendMessage(ctx, jid, msg)
     if err != nil {
         log.Println("Failed to send message:", err)
         http.Error(w, "Failed to send message", http.StatusInternalServerError)
         return
     }
 
     log.Printf("Message sent to %s: %s", req.To, req.Message)
     w.Write([]byte("Message sent"))
 }
