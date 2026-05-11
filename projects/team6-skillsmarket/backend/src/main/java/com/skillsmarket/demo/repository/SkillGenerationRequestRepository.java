package com.skillsmarket.demo.repository;

import com.skillsmarket.demo.domain.SkillGenerationRequest;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SkillGenerationRequestRepository extends JpaRepository<SkillGenerationRequest, Long> {
}
