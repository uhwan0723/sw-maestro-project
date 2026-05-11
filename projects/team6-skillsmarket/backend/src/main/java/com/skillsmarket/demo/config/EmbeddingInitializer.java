package com.skillsmarket.demo.config;

import com.skillsmarket.demo.service.SkillEmbeddingService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class EmbeddingInitializer {

    private final SkillEmbeddingService skillEmbeddingService;

    @Value("${spring.ai.openai.api-key:}")
    private String openAiApiKey;

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        if (openAiApiKey == null || openAiApiKey.isBlank()) {
            log.warn("OpenAI API key가 설정되지 않아 임베딩 초기화를 건너뜁니다.");
            return;
        }
        log.info("애플리케이션 시작 완료 - 스킬 임베딩을 시작합니다.");
        skillEmbeddingService.embedAllSkills();
        log.info("스킬 임베딩이 완료되었습니다.");
    }
}
