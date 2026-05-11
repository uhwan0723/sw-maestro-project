package com.skillsmarket.demo.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import com.skillsmarket.demo.service.SkillGenerationService;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.ApplicationContext;
import org.springframework.http.MediaType;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@ActiveProfiles("test")
@AutoConfigureMockMvc
@org.springframework.context.annotation.Import(TestChatClientConfig.class)
class AsyncConfigTest {

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private SkillGenerationRequestRepository repository;

    @Autowired
    private SkillGenerationService skillGenerationService;

    @Autowired
    @Qualifier("skillGenerationExecutor")
    private Executor skillGenerationExecutor;

    @BeforeEach
    void setUp() {
        repository.deleteAll();
    }

    @Test
    void ThreadPoolTaskExecutor_빈이_정상_로드되는지_검증() {
        // AC 7
        assertThat(applicationContext.containsBean("skillGenerationExecutor")).isTrue();
        assertThat(skillGenerationExecutor).isInstanceOf(ThreadPoolTaskExecutor.class);

        ThreadPoolTaskExecutor executor = (ThreadPoolTaskExecutor) skillGenerationExecutor;
        assertThat(executor.getCorePoolSize()).isEqualTo(2);
        assertThat(executor.getMaxPoolSize()).isEqualTo(5);
    }

    @Test
    void Async_메서드_호출_후_즉시_반환되는지_확인() {
        // AC 5: @Async 메서드 호출 후 즉시 반환
        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 프롬프트");
        SkillGenerationRequest saved = repository.save(request);

        long start = System.currentTimeMillis();
        skillGenerationService.runPipeline(saved.getId());
        long elapsed = System.currentTimeMillis() - start;

        // The async call should return almost immediately (well under 1 second)
        assertThat(elapsed).isLessThan(1000);
    }

    @Test
    void POST_generate_호출_시_202_즉시_반환_후_상태_변경_확인() throws Exception {
        // AC 6: Awaitility로 비동기 처리 확인
        MvcResult result = mockMvc.perform(post("/skills/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userPrompt": "비동기 테스트용 스킬"}
                                """))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.status").value("PENDING"))
                .andReturn();

        String responseBody = result.getResponse().getContentAsString();
        Long requestId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
                .readTree(responseBody).get("requestId").asLong();

        // Wait until the async pipeline finishes and status changes from PENDING
        await().atMost(10, TimeUnit.SECONDS)
                .pollInterval(200, TimeUnit.MILLISECONDS)
                .untilAsserted(() -> {
                    SkillGenerationRequest updated = repository.findById(requestId).orElseThrow();
                    assertThat(updated.getStatus()).isNotEqualTo(GenerationStatus.PENDING);
                });

        // Verify the final status is COMPLETED
        SkillGenerationRequest finalState = repository.findById(requestId).orElseThrow();
        assertThat(finalState.getStatus()).isEqualTo(GenerationStatus.COMPLETED);
    }
}
