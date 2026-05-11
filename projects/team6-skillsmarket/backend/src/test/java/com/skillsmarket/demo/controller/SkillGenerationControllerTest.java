package com.skillsmarket.demo.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@ActiveProfiles("test")
@AutoConfigureMockMvc
@org.springframework.context.annotation.Import(com.skillsmarket.demo.config.TestChatClientConfig.class)
class SkillGenerationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private SkillGenerationRequestRepository repository;

    @BeforeEach
    void setUp() {
        repository.deleteAll();
    }

    @Test
    void 유효한_userPrompt_전송_시_202_반환_및_requestId_포함() throws Exception {
        mockMvc.perform(post("/skills/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userPrompt": "Spring Boot REST API 스킬 만들어줘"}
                                """))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.requestId").isNotEmpty())
                .andExpect(jsonPath("$.status").value("PENDING"));
    }

    @Test
    void 빈_userPrompt_전송_시_400_반환() throws Exception {
        mockMvc.perform(post("/skills/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userPrompt": "   "}
                                """))
                .andExpect(status().isBadRequest());
    }

    @Test
    void userPrompt_누락_시_400_반환() throws Exception {
        mockMvc.perform(post("/skills/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void 응답의_status가_PENDING인지_확인() throws Exception {
        mockMvc.perform(post("/skills/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userPrompt": "React Hooks 스킬 만들어줘"}
                                """))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.status").value("PENDING"));
    }

    @Test
    void DB에_요청이_실제로_저장되었는지_확인() throws Exception {
        // when
        MvcResult result = mockMvc.perform(post("/skills/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userPrompt": "Docker 스킬 만들어줘"}
                                """))
                .andExpect(status().isAccepted())
                .andReturn();

        String responseBody = result.getResponse().getContentAsString();
        Long requestId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
                .readTree(responseBody).get("requestId").asLong();

        // then
        SkillGenerationRequest saved = repository.findById(requestId).orElseThrow();
        assertThat(saved.getUserPrompt()).isEqualTo("Docker 스킬 만들어줘");
        assertThat(saved.getStatus()).isEqualTo(GenerationStatus.PENDING);
        assertThat(saved.getCreatedAt()).isNotNull();
    }

    @Test
    void 존재하는_요청_조회_시_200_및_status_필드_확인() throws Exception {
        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 스킬 요청");
        SkillGenerationRequest saved = repository.save(request);

        mockMvc.perform(get("/skills/generate/{requestId}", saved.getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.requestId").value(saved.getId()))
                .andExpect(jsonPath("$.status").value("PENDING"));
    }

    @Test
    void COMPLETED_상태_요청_조회_시_finalSkillContent_포함_확인() throws Exception {
        SkillGenerationRequest request = SkillGenerationRequest.create("완료된 스킬 요청");
        request.updateStatus(GenerationStatus.COMPLETED);
        ReflectionTestUtils.setField(request, "finalSkillContent", "# 최종 스킬 내용");
        SkillGenerationRequest saved = repository.save(request);

        mockMvc.perform(get("/skills/generate/{requestId}", saved.getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("COMPLETED"))
                .andExpect(jsonPath("$.finalSkillContent").value("# 최종 스킬 내용"));
    }

    @Test
    void 존재하지_않는_id_조회_시_404_반환() throws Exception {
        mockMvc.perform(get("/skills/generate/{requestId}", 999999L))
                .andExpect(status().isNotFound());
    }

    @Test
    void SSE_연결_시_200_및_text_event_stream_Content_Type_확인() throws Exception {
        SkillGenerationRequest request = SkillGenerationRequest.create("SSE 테스트 요청");
        SkillGenerationRequest saved = repository.save(request);

        mockMvc.perform(get("/skills/generate/{requestId}/stream", saved.getId())
                        .accept(MediaType.TEXT_EVENT_STREAM))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM));
    }
}
