package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@SpringBootApplication
@RestController
public class DemoApplication {

    @Value("${app.name:demo-app}")
    private String appName;
    
    @Value("${app.version:1.0.0}")
    private String appVersion;
    
    @Value("${app.environment:development}")
    private String environment;

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }

    @GetMapping("/")
    public ResponseEntity<Map<String, Object>> home() {
        Map<String, Object> response = new HashMap<>();
        response.put("message", "Welcome to the Demo Application!");
        response.put("application", appName);
        response.put("version", appVersion);
        response.put("environment", environment);
        response.put("timestamp", LocalDateTime.now());
        response.put("status", "running");
        
        return ResponseEntity.ok(response);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "UP");
        response.put("application", appName);
        response.put("version", appVersion);
        response.put("timestamp", LocalDateTime.now());
        
        return ResponseEntity.ok(response);
    }

    @GetMapping("/info")
    public ResponseEntity<Map<String, Object>> info() {
        Map<String, Object> response = new HashMap<>();
        response.put("application", Map.of(
            "name", appName,
            "version", appVersion,
            "environment", environment
        ));
        response.put("system", Map.of(
            "java.version", System.getProperty("java.version"),
            "os.name", System.getProperty("os.name"),
            "os.arch", System.getProperty("os.arch")
        ));
        response.put("timestamp", LocalDateTime.now());
        
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/demo")
    public ResponseEntity<Map<String, Object>> demoApi() {
        Map<String, Object> response = new HashMap<>();
        response.put("message", "This is a demo API endpoint");
        response.put("data", Map.of(
            "items", new String[]{"item1", "item2", "item3"},
            "count", 3,
            "success", true
        ));
        response.put("timestamp", LocalDateTime.now());
        
        return ResponseEntity.ok(response);
    }
}