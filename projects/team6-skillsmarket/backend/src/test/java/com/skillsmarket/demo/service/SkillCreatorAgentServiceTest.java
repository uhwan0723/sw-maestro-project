package com.skillsmarket.demo.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.ChatClient.CallResponseSpec;
import org.springframework.ai.chat.client.ChatClient.ChatClientRequestSpec;
import org.springframework.test.util.ReflectionTestUtils;

class SkillCreatorAgentServiceTest {

    private ChatClient chatClient;
    private SkillGenerationRequestRepository repository;
    private SseEmitterService sseEmitterService;
    private SkillCreatorAgentService skillCreatorAgentService;

    @BeforeEach
    void setUp() {
        chatClient = mock(ChatClient.class);
        repository = mock(SkillGenerationRequestRepository.class);
        sseEmitterService = mock(SseEmitterService.class);

        skillCreatorAgentService = new SkillCreatorAgentService(
                mock(ChatClient.Builder.class),
                repository,
                sseEmitterService
        );
        ReflectionTestUtils.setField(skillCreatorAgentService, "chatClient", chatClient);
    }

    private void setupChatClientMock(String response) {
        ChatClientRequestSpec requestSpec = mock(ChatClientRequestSpec.class);
        CallResponseSpec callResponseSpec = mock(CallResponseSpec.class);

        when(chatClient.prompt()).thenReturn(requestSpec);
        when(requestSpec.system(any(String.class))).thenReturn(requestSpec);
        when(requestSpec.user(any(String.class))).thenReturn(requestSpec);
        when(requestSpec.call()).thenReturn(callResponseSpec);
        when(callResponseSpec.content()).thenReturn(response);
    }

    @Test
    void generate_호출_시_generatedSkillContent_저장_및_status가_REVIEWING으로_전환() {
        // given
        String generatedSkill = "# 테스트 스킬\n테스트 설명\n\n## 트리거 조건\n- 테스트 트리거";

        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 프롬프트");
        ReflectionTestUtils.setField(request, "id", 1L);
        request.updateClarifiedRequirements("구조화된 요구사항");
        request.updateStatus(GenerationStatus.GENERATING);

        when(repository.findById(1L)).thenReturn(Optional.of(request));
        when(repository.save(any())).thenReturn(request);
        setupChatClientMock(generatedSkill);

        // when
        String result = skillCreatorAgentService.generate(1L);

        // then
        assertThat(result).isEqualTo(generatedSkill);
        assertThat(request.getGeneratedSkillContent()).isEqualTo(generatedSkill);
        assertThat(request.getStatus()).isEqualTo(GenerationStatus.REVIEWING);

        verify(repository).save(request);
        verify(sseEmitterService).sendEvent(1L, GenerationStatus.REVIEWING);
    }

    @Test
    void refine_호출_시_reviewFeedback_포함하여_개선된_스킬_반환() {
        // given
        String originalSkill = "# 원본 스킬\n설명";
        String refinedSkill = "# 개선된 스킬\n개선된 설명\n\n## 트리거 조건\n- 개선된 트리거";
        String reviewFeedback = "트리거 조건을 추가해주세요.";

        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 프롬프트");
        ReflectionTestUtils.setField(request, "id", 1L);
        request.updateGeneratedSkillContent(originalSkill);
        request.updateStatus(GenerationStatus.REVIEWING);

        when(repository.findById(1L)).thenReturn(Optional.of(request));
        setupChatClientMock(refinedSkill);

        // when
        String result = skillCreatorAgentService.refine(1L, reviewFeedback);

        // then
        assertThat(result).isEqualTo(refinedSkill);
    }
}
