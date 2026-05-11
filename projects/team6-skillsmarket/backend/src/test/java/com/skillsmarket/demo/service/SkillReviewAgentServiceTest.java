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

class SkillReviewAgentServiceTest {

    private ChatClient chatClient;
    private SkillGenerationRequestRepository repository;
    private SkillReviewAgentService skillReviewAgentService;

    @BeforeEach
    void setUp() {
        chatClient = mock(ChatClient.class);
        repository = mock(SkillGenerationRequestRepository.class);

        skillReviewAgentService = new SkillReviewAgentService(
                mock(ChatClient.Builder.class),
                repository
        );
        ReflectionTestUtils.setField(skillReviewAgentService, "chatClient", chatClient);
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
    void review_호출_시_reviewFeedback_저장_확인() {
        // given
        String generatedSkill = "# 테스트 스킬\n설명\n\n## 트리거 조건\n- 트리거";
        String reviewFeedback = "**품질**: 지시사항이 명확합니다.\n**완성도**: 예시 섹션이 부족합니다.\n**보안**: 문제 없음.\n**사용성**: 트리거 조건을 더 구체적으로 작성해주세요.";

        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 프롬프트");
        ReflectionTestUtils.setField(request, "id", 1L);
        request.updateGeneratedSkillContent(generatedSkill);
        request.updateStatus(GenerationStatus.REVIEWING);

        when(repository.findById(1L)).thenReturn(Optional.of(request));
        when(repository.save(any())).thenReturn(request);
        setupChatClientMock(reviewFeedback);

        // when
        String result = skillReviewAgentService.review(1L);

        // then
        assertThat(result).isEqualTo(reviewFeedback);
        assertThat(request.getReviewFeedback()).isEqualTo(reviewFeedback);
        verify(repository).save(request);
    }
}
