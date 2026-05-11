package com.skillsmarket.demo.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.skillsmarket.demo.domain.GenerationStatus;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Slf4j
@Service
public class SseEmitterService {

    private static final long SSE_TIMEOUT = 5 * 60 * 1000L; // 5 minutes

    private final Map<Long, SseEmitter> emitters = new ConcurrentHashMap<>();

    public SseEmitter createEmitter(Long requestId) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT);
        emitters.put(requestId, emitter);

        emitter.onCompletion(() -> {
            log.info("SSE emitter completed for requestId={}", requestId);
            emitters.remove(requestId);
        });
        emitter.onTimeout(() -> {
            log.info("SSE emitter timed out for requestId={}", requestId);
            emitters.remove(requestId);
        });
        emitter.onError(e -> {
            log.warn("SSE emitter error for requestId={}", requestId, e);
            emitters.remove(requestId);
        });

        return emitter;
    }

    public void sendEvent(Long requestId, GenerationStatus status) {
        SseEmitter emitter = emitters.get(requestId);
        if (emitter == null) {
            return;
        }
        try {
            String json = "{\"requestId\":" + requestId + ",\"status\":\"" + status.name() + "\"}";
            emitter.send(SseEmitter.event().data(json, org.springframework.http.MediaType.APPLICATION_JSON));
        } catch (IOException e) {
            log.warn("Failed to send SSE event for requestId={}", requestId, e);
            emitters.remove(requestId);
        }
    }

    public void sendCompletedEvent(Long requestId, String finalSkillContent) {
        SseEmitter emitter = emitters.get(requestId);
        if (emitter == null) {
            return;
        }
        try {
            ObjectMapper mapper = new ObjectMapper();
            Map<String, Object> payload = Map.of(
                    "requestId", requestId,
                    "status", "COMPLETED",
                    "finalSkillContent", finalSkillContent != null ? finalSkillContent : ""
            );
            emitter.send(SseEmitter.event().data(mapper.writeValueAsString(payload), org.springframework.http.MediaType.APPLICATION_JSON));
        } catch (IOException e) {
            log.warn("Failed to send COMPLETED SSE event for requestId={}", requestId, e);
            emitters.remove(requestId);
        }
    }

    public void completeEmitter(Long requestId) {
        SseEmitter emitter = emitters.get(requestId);
        if (emitter != null) {
            emitter.complete();
            emitters.remove(requestId);
        }
    }

    public void removeEmitter(Long requestId) {
        emitters.remove(requestId);
    }

    // For testing purposes
    boolean hasEmitter(Long requestId) {
        return emitters.containsKey(requestId);
    }
}
