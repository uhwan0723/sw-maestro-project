package com.skillsmarket.demo.repository;

import com.skillsmarket.demo.domain.SkillCategory;
import com.skillsmarket.demo.domain.Skills;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SkillsRepository extends JpaRepository<Skills, Long> {

    List<Skills> findByCategory(SkillCategory category);
}
