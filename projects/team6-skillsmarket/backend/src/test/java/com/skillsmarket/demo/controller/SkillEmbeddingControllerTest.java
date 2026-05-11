package com.skillsmarket.demo.controller;

import static io.restassured.module.mockmvc.RestAssuredMockMvc.given;
import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.notNullValue;
import static org.junit.jupiter.api.Assertions.assertAll;

import com.skillsmarket.demo.domain.SkillCategory;
import com.skillsmarket.demo.domain.Skills;
import com.skillsmarket.demo.dto.SimilarSkillResponses;
import com.skillsmarket.demo.repository.SkillsRepository;
import io.restassured.module.mockmvc.RestAssuredMockMvc;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.context.WebApplicationContext;

@SpringBootTest
@ActiveProfiles("test")
@EnabledIfEnvironmentVariable(named = "OPENAI_API_KEY", matches = ".+")
class SkillEmbeddingControllerTest {

    @Autowired
    private WebApplicationContext webApplicationContext;

    @Autowired
    private SkillsRepository skillsRepository;

    @Autowired
    private VectorStore vectorStore;

    @BeforeEach
    void setUp() {
        RestAssuredMockMvc.webAppContextSetup(webApplicationContext);
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
    void POST_embed_all_200_반환() {
        // given
        skillsRepository.save(createTestSkill(
                "Spring Boot REST API",
                "Spring Boot로 RESTful API 개발하기",
                SkillCategory.SPRING_BOOT,
                "Spring Boot는 Java 기반의 웹 프레임워크로, RESTful API를 쉽게 개발할 수 있습니다."
        ));

        // when & then
        given()
                .when()
                .post("/skills/embed-all")
                .then()
                .statusCode(200);
    }

    @Test
    void GET_recommendation_유사스킬_반환() {
        // given
        skillsRepository.save(createTestSkill(
                "Spring Boot REST API",
                "Spring Boot로 RESTful API 개발하기",
                SkillCategory.SPRING_BOOT,
                "Spring Boot는 Java 기반의 백엔드 웹 프레임워크로, RESTful API를 쉽게 개발할 수 있습니다."
        ));
        skillsRepository.save(createTestSkill(
                "React Hooks",
                "React Hooks 심화 학습",
                SkillCategory.REACT,
                "React Hooks는 프론트엔드 JavaScript 라이브러리의 함수형 컴포넌트에서 상태 관리 기능입니다."
        ));
        skillsRepository.save(createTestSkill(
                "Docker & Kubernetes",
                "컨테이너 오케스트레이션",
                SkillCategory.DEVOPS,
                "Docker는 컨테이너 기반 가상화 플랫폼이고, Kubernetes는 컨테이너 오케스트레이션 도구입니다."
        ));

        // 임베딩 먼저 수행
        given()
                .when()
                .post("/skills/embed-all")
                .then()
                .statusCode(200);

        // when & then
        given()
                .queryParam("query", "Java backend framework")
                .queryParam("topK", 3)
                .when()
                .get("/skills/recommendation")
                .then()
                .statusCode(200)
                .body("skills", hasSize(3))
                .body("skills[0].title", equalTo("Spring Boot REST API"))
                .body("skills[0].id", notNullValue())
                .body("skills[0].description", notNullValue())
                .body("skills[0].percentage", greaterThan(0));
    }

    @Test
    void GET_recommendation_기본_topK_동작() {
        // given
        skillsRepository.save(
                createTestSkill("Skill 1", "desc1", SkillCategory.SPRING_BOOT, "Java Spring Boot 백엔드 개발"));
        skillsRepository.save(createTestSkill("Skill 2", "desc2", SkillCategory.REACT, "React 프론트엔드 개발"));
        skillsRepository.save(createTestSkill("Skill 3", "desc3", SkillCategory.DEVOPS, "DevOps CI/CD 파이프라인"));
        skillsRepository.save(createTestSkill("Skill 4", "desc4", SkillCategory.DATA, "데이터 분석 및 머신러닝"));
        skillsRepository.save(createTestSkill("Skill 5", "desc5", SkillCategory.ETC, "프로젝트 매니지먼트"));

        given().when().post("/skills/embed-all").then().statusCode(200);

        // when & then - topK 생략 시 기본값 3
        given()
                .queryParam("query", "programming")
                .when()
                .get("/skills/recommendation")
                .then()
                .statusCode(200)
                .body("skills", hasSize(3));
    }

    @Test
    void GET_recommendation_커스텀_topK() {
        // given
        skillsRepository.save(
                createTestSkill("Skill 1", "desc1", SkillCategory.SPRING_BOOT, "Java Spring Boot 백엔드 개발"));
        skillsRepository.save(createTestSkill("Skill 2", "desc2", SkillCategory.REACT, "React 프론트엔드 개발"));
        skillsRepository.save(createTestSkill("Skill 3", "desc3", SkillCategory.DEVOPS, "DevOps CI/CD 파이프라인"));

        given().when().post("/skills/embed-all").then().statusCode(200);

        // when & then
        given()
                .queryParam("query", "programming")
                .queryParam("topK", 1)
                .when()
                .get("/skills/recommendation")
                .then()
                .statusCode(200)
                .body("skills", hasSize(1));
    }

    @Test
    void GET_recommendation_query_없으면_400() {
        // when & then
        given()
                .when()
                .get("/skills/recommendation")
                .then()
                .statusCode(400);
    }

    @Test
    void 전체플로우_임베딩_후_추천() {
        // given
        skillsRepository.save(createTestSkill(
                "Spring Security OAuth2",
                "인증과 보안 구현",
                SkillCategory.SPRING_BOOT,
                "Spring Security는 인증(Authentication)과 인가(Authorization)를 처리하는 프레임워크입니다. OAuth2, JWT 토큰 기반 인증을 지원합니다."
        ));
        skillsRepository.save(createTestSkill(
                "React State Management",
                "상태 관리 패턴",
                SkillCategory.REACT,
                "React에서 Redux, Context API, Zustand 등을 활용한 전역 상태 관리 패턴을 학습합니다."
        ));
        skillsRepository.save(createTestSkill(
                "AWS Deployment",
                "클라우드 배포",
                SkillCategory.DEVOPS,
                "AWS EC2, ECS, Lambda를 활용한 애플리케이션 배포 및 인프라 구성을 다룹니다."
        ));

        // 임베딩
        given()
                .when()
                .post("/skills/embed-all")
                .then()
                .statusCode(200);

        // when & then - 한국어 쿼리로 검색
        SimilarSkillResponses responses = given()
                .queryParam("query", "인증과 보안")
                .queryParam("topK", 2)
                .when()
                .get("/skills/recommendation")
                .then()
                .statusCode(200)
                .extract().as(SimilarSkillResponses.class);

        assertAll(
                () -> assertThat(responses.skills()).hasSize(2),
                () -> assertThat(responses.skills().get(0).title()).isEqualTo("Spring Security OAuth2"),
                () -> assertThat(responses.skills().get(0).percentage()).isGreaterThan(0)
        );
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
