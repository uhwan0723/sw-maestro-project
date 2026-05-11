package com.skillsmarket.demo.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertAll;

import com.skillsmarket.demo.domain.SkillCategory;
import com.skillsmarket.demo.domain.Skills;
import com.skillsmarket.demo.dto.SimilarSkillResponse;
import com.skillsmarket.demo.dto.SimilarSkillResponses;
import com.skillsmarket.demo.repository.SkillsRepository;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.util.ReflectionTestUtils;

@SpringBootTest
@ActiveProfiles("test")
@EnabledIfEnvironmentVariable(named = "OPENAI_API_KEY", matches = ".+")
class SkillEmbeddingServiceTest {

    @Autowired
    private SkillEmbeddingService skillEmbeddingService;

    @Autowired
    private SkillsRepository skillsRepository;

    @Autowired
    private VectorStore vectorStore;

    @BeforeEach
    void setUp() {
        // VectorStore에서 기존 임베딩 삭제
        List<String> existingIds = skillsRepository.findAll().stream()
                .map(s -> "skill-" + s.getId())
                .toList();
        if (!existingIds.isEmpty()) {
            vectorStore.delete(existingIds);
        }
        skillsRepository.deleteAll();
    }

    @Test
    void embedAllSkills_임베딩후_유사도검색_성공() {
        // given
        skillsRepository.save(createTestSkill(
                "Spring Boot REST API",
                "Spring Boot로 RESTful API 개발하기",
                SkillCategory.SPRING_BOOT,
                "Spring Boot는 Java 기반의 웹 프레임워크로, RESTful API를 쉽게 개발할 수 있습니다. Spring MVC, JPA, Security 등을 활용합니다."
        ));
        skillsRepository.save(createTestSkill(
                "React Hooks",
                "React Hooks 심화 학습",
                SkillCategory.REACT,
                "React Hooks는 함수형 컴포넌트에서 상태 관리와 생명주기를 다루는 기능입니다. useState, useEffect, useContext 등이 있습니다."
        ));
        skillsRepository.save(createTestSkill(
                "Docker & Kubernetes",
                "컨테이너 오케스트레이션",
                SkillCategory.DEVOPS,
                "Docker는 컨테이너 기반 가상화 플랫폼이고, Kubernetes는 컨테이너 오케스트레이션 도구입니다. 배포 자동화에 사용됩니다."
        ));

        // when
        skillEmbeddingService.embedAllSkills();

        // then
        List<Document> results = vectorStore.similaritySearch(
                SearchRequest.builder().query("Spring Boot").topK(3).build()
        );
        assertAll(
                () -> assertThat(results).isNotEmpty(),
                () -> assertThat(results.get(0).getMetadata().get("title")).isEqualTo("Spring Boot REST API")
        );
    }

    @Test
    void findSimilarSkills_의미적으로_관련된_결과_우선_반환() {
        // given
        skillsRepository.save(createTestSkill(
                "Spring Boot REST API",
                "Spring Boot로 RESTful API 개발하기",
                SkillCategory.SPRING_BOOT,
                "Spring Boot는 Java 기반의 백엔드 웹 프레임워크로, RESTful API를 쉽게 개발할 수 있습니다. Spring MVC, JPA, Security 등을 활용합니다."
        ));
        skillsRepository.save(createTestSkill(
                "React Hooks",
                "React Hooks 심화 학습",
                SkillCategory.REACT,
                "React Hooks는 프론트엔드 JavaScript 라이브러리의 함수형 컴포넌트에서 상태 관리와 생명주기를 다루는 기능입니다."
        ));
        skillsRepository.save(createTestSkill(
                "Docker & Kubernetes",
                "컨테이너 오케스트레이션",
                SkillCategory.DEVOPS,
                "Docker는 컨테이너 기반 가상화 플랫폼이고, Kubernetes는 컨테이너 오케스트레이션 도구입니다."
        ));
        skillEmbeddingService.embedAllSkills();

        // when
        SimilarSkillResponses results = skillEmbeddingService.findSimilarSkills("Java backend framework", 3);

        // then
        assertAll(
                () -> assertThat(results.skills()).isNotEmpty(),
                () -> assertThat(results.skills().get(0).title()).isEqualTo("Spring Boot REST API")
        );
    }

    @Test
    void findSimilarSkills_topK_파라미터_동작() {
        // given
        skillsRepository.save(createTestSkill("Skill 1", "desc1", SkillCategory.SPRING_BOOT, "Java Spring Boot 백엔드 개발"));
        skillsRepository.save(createTestSkill("Skill 2", "desc2", SkillCategory.REACT, "React 프론트엔드 개발"));
        skillsRepository.save(createTestSkill("Skill 3", "desc3", SkillCategory.DEVOPS, "DevOps CI/CD 파이프라인"));
        skillsRepository.save(createTestSkill("Skill 4", "desc4", SkillCategory.DATA, "데이터 분석 및 머신러닝"));
        skillsRepository.save(createTestSkill("Skill 5", "desc5", SkillCategory.ETC, "프로젝트 매니지먼트"));
        skillEmbeddingService.embedAllSkills();

        // when
        SimilarSkillResponses results = skillEmbeddingService.findSimilarSkills("programming", 2);

        // then
        assertThat(results.skills()).hasSize(2);
    }

    @Test
    void findSimilarSkills_응답_구조_검증() {
        // given
        Skills saved = skillsRepository.save(createTestSkill(
                "Spring Security",
                "인증과 인가 구현",
                SkillCategory.SPRING_BOOT,
                "Spring Security는 인증(Authentication)과 인가(Authorization)를 처리하는 프레임워크입니다. OAuth2, JWT 등을 지원합니다."
        ));
        skillEmbeddingService.embedAllSkills();

        // when
        SimilarSkillResponses results = skillEmbeddingService.findSimilarSkills("Spring 보안 인증", 1);

        // then
        SimilarSkillResponse response = results.skills().get(0);

        assertAll(
                () -> assertThat(results.skills()).hasSize(1),
                () -> assertThat(response.id()).isEqualTo(saved.getId()),
                () -> assertThat(response.title()).isEqualTo("Spring Security"),
                () -> assertThat(response.description()).isEqualTo("인증과 인가 구현"),
                () -> assertThat(response.percentage()).isBetween(0, 100)
        );
    }

    @Test
    void embedAllSkills_빈테이블_처리() {
        // given - 스킬 없음

        // when & then - 에러 없이 동작
        skillEmbeddingService.embedAllSkills();

        SimilarSkillResponses results = skillEmbeddingService.findSimilarSkills("anything", 3);
        assertThat(results.skills()).isEmpty();
    }

    private Skills createTestSkill(String title, String description, SkillCategory category, String content) {
        Skills skill = new Skills();
        ReflectionTestUtils.setField(skill, "title", title);
        ReflectionTestUtils.setField(skill, "description", description);
        ReflectionTestUtils.setField(skill, "category", category);
        ReflectionTestUtils.setField(skill, "content", content);
        return skill;
    }
}
