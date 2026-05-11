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

class DeepthinkServiceTest {

    private ChatClient chatClient;
    private SkillGenerationRequestRepository repository;
    private SseEmitterService sseEmitterService;
    private DeepthinkService deepthinkService;

    @BeforeEach
    void setUp() {
        chatClient = mock(ChatClient.class);
        repository = mock(SkillGenerationRequestRepository.class);
        sseEmitterService = mock(SseEmitterService.class);

        deepthinkService = new DeepthinkService(
                mock(ChatClient.Builder.class),
                repository,
                sseEmitterService
        );
        // Inject the mocked chatClient directly
        ReflectionTestUtils.setField(deepthinkService, "chatClient", chatClient);
    }

    @Test
    void clarify_호출_시_status가_GENERATING으로_전환되고_저장됨() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 프롬프트");
        ReflectionTestUtils.setField(request, "id", 1L);
        request.updateStatus(GenerationStatus.CLARIFYING);

        when(repository.findById(1L)).thenReturn(Optional.of(request));
        when(repository.save(any())).thenReturn(request);

        ChatClientRequestSpec requestSpec = mock(ChatClientRequestSpec.class);
        CallResponseSpec callResponseSpec = mock(CallResponseSpec.class);

        when(chatClient.prompt()).thenReturn(requestSpec);
        when(requestSpec.system(any(String.class))).thenReturn(requestSpec);
        when(requestSpec.user(any(String.class))).thenReturn(requestSpec);
        when(requestSpec.call()).thenReturn(callResponseSpec);
        when(callResponseSpec.content()).thenReturn("구조화된 요구사항 결과");

        // when
        String result = deepthinkService.clarify(1L);

        // then
        assertThat(result).isEqualTo("구조화된 요구사항 결과");
        assertThat(request.getStatus()).isEqualTo(GenerationStatus.GENERATING);
        assertThat(request.getClarifiedRequirements()).isEqualTo("구조화된 요구사항 결과");

        verify(repository).save(request);
        verify(sseEmitterService).sendEvent(1L, GenerationStatus.GENERATING);
    }
}
