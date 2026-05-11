package com.skillsmarket.demo.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.skillsmarket.demo.domain.GenerationStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

class SseEmitterServiceTest {

    private SseEmitterService sseEmitterService;

    @BeforeEach
    void setUp() {
        sseEmitterService = new SseEmitterService();
    }

    @Test
    void emitter_등록_시_조회_가능() {
        // when
        SseEmitter emitter = sseEmitterService.createEmitter(1L);

        // then
        assertThat(emitter).isNotNull();
        assertThat(sseEmitterService.hasEmitter(1L)).isTrue();
    }

    @Test
    void emitter_제거_시_더_이상_조회_불가() {
        // given
        sseEmitterService.createEmitter(1L);

        // when
        sseEmitterService.removeEmitter(1L);

        // then
        assertThat(sseEmitterService.hasEmitter(1L)).isFalse();
    }

    @Test
    void emitter_완료_시_제거됨() {
        // given
        sseEmitterService.createEmitter(1L);

        // when
        sseEmitterService.completeEmitter(1L);

        // then
        assertThat(sseEmitterService.hasEmitter(1L)).isFalse();
    }

    @Test
    void 이벤트_발행_시_예외_없이_동작() {
        // given
        sseEmitterService.createEmitter(1L);

        // when & then - no exception
        sseEmitterService.sendEvent(1L, GenerationStatus.CLARIFYING);
    }

    @Test
    void 존재하지_않는_emitter에_이벤트_발행_시_예외_없이_무시() {
        // when & then - no exception
        sseEmitterService.sendEvent(999L, GenerationStatus.CLARIFYING);
    }

    @Test
    void 존재하지_않는_emitter_완료_시_예외_없이_무시() {
        // when & then - no exception
        sseEmitterService.completeEmitter(999L);
    }
}
