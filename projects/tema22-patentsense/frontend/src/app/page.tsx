"use client";

import React, { useState, useRef, useEffect } from 'react';
import {
  Search, AlertTriangle, CheckCircle, Shield,
  Loader2, Lightbulb, FileText, Info, Sparkles,
  ArrowRight, ClipboardCheck, XCircle
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import styles from './page.module.css';

type LogEntry = {
  id: string;
  step: string;
  message: string;
  data?: any;
  status: 'pending' | 'success' | 'error';
};

type HistoryItem = {
  id: string;
  timestamp: number;
  formData: { title: string; background: string; details: string; effect: string; };
  result?: any;
};

export default function DemoPage() {
  const [formData, setFormData] = useState({ title: '', background: '', details: '', effect: '' });
  const [appState, setAppState] = useState<'idle' | 'processing' | 'result'>('idle');
  const [step, setStep] = useState(0);

  // History state
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // For backend integration
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [result, setResult] = useState<any>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const STEPS = ['아이디어 구조화', 'KIPRIS DB 검색', '유사도 산출', '청구항 분석', '리포트 생성'];

  const isFormValid = formData.title && formData.details;

  // Auto-scroll raw logs if needed
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Load history from local storage
  useEffect(() => {
    const saved = localStorage.getItem('ideaHistory');
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }
  }, []);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!isFormValid || appState === 'processing') return;

    setAppState('processing');
    setStep(0);
    setLogs([]);
    setResult(null);

    // Save to history
    const newHistoryItem: HistoryItem = {
      id: Date.now().toString(),
      timestamp: Date.now(),
      formData: { ...formData }
    };

    // Avoid duplicate history saving if title and details are exactly same as latest
    const isDuplicate = history.length > 0 &&
      history[0].formData.title === formData.title &&
      history[0].formData.details === formData.details;

    if (!isDuplicate) {
      const updatedHistory = [newHistoryItem, ...history].slice(0, 50); // Keep last 50
      setHistory(updatedHistory);
      localStorage.setItem('ideaHistory', JSON.stringify(updatedHistory));
    }

    // Merge form data into a single text for backend
    const combinedIdeaText = `
[발명의 명칭]
${formData.title}

[해결하려는 과제 (배경)]
${formData.background}

[구체적 내용 (수단)]
${formData.details}

[기대 효과]
${formData.effect}
    `.trim();

    try {
      const response = await fetch("http://localhost:8000/v1/analyze/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea_text: combinedIdeaText }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader available");

      const decoder = new TextDecoder();
      let buffer = "";

      let currentStepIndex = 0;
      let lastStepName = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEventName = 'message';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEventName = line.substring(7).trim();
          } else if (line.startsWith('data: ')) {
            const dataStr = line.substring(6).trim();
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr);

                // Handle different event types
                if (currentEventName === 'status' || currentEventName === 'progress') {

                  // Progress UI step
                  if (data.step !== lastStepName) {
                    lastStepName = data.step;
                    if (currentStepIndex < STEPS.length - 1) {
                      currentStepIndex++;
                      setStep(currentStepIndex);
                    }
                  }

                  setLogs(prev => [...prev, {
                    id: Date.now().toString() + Math.random().toString(),
                    step: data.step,
                    message: data.message,
                    data: data.data,
                    status: 'success'
                  }]);

                } else if (currentEventName === 'done') {
                  setStep(STEPS.length - 1);
                  setLogs(prev => [...prev, {
                    id: 'done',
                    step: data.step,
                    message: data.message,
                    status: 'success'
                  }]);
                  setResult(data.data);
                  setAppState('result');

                  // Update history item with result
                  if (!isDuplicate) {
                    setHistory(prev => {
                      if (prev.length > 0 && prev[0].id === newHistoryItem.id) {
                        const updated = [...prev];
                        updated[0] = { ...updated[0], result: data.data };
                        localStorage.setItem('ideaHistory', JSON.stringify(updated));
                        return updated;
                      }
                      return prev;
                    });
                  }

                } else if (currentEventName === 'error') {
                  setLogs(prev => [...prev, {
                    id: 'error',
                    step: data.step,
                    message: data.message,
                    status: 'error'
                  }]);
                  setAppState('idle');
                  alert(`에러 발생: ${data.message}`);
                }
              } catch (e) {
                console.error("Failed to parse SSE data", e);
              }
            }
          }
        }
      }
    } catch (err: any) {
      setLogs(prev => [...prev, {
        id: 'fatal_error',
        step: 'network',
        message: err.message || "Failed to connect to the server.",
        status: 'error'
      }]);
      setAppState('idle');
      alert(`네트워크 에러: ${err.message || "Failed to connect to the server."}`);
    }
  };

  const resetForm = () => {
    setAppState('idle');
    setFormData({ title: '', background: '', details: '', effect: '' });
    setLogs([]);
    setResult(null);
  };

  const loadHistoryItem = (item: HistoryItem) => {
    if (appState === 'processing') return;
    setFormData(item.formData);
    setLogs([]);
    if (item.result) {
      setResult(item.result);
      setAppState('result');
      setStep(STEPS.length - 1);
    } else {
      setResult(null);
      setAppState('idle');
      setStep(0);
    }
  };

  const deleteHistoryItem = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setHistory(prev => {
      const updated = prev.filter(item => item.id !== id);
      localStorage.setItem('ideaHistory', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <div className={styles.container}>
      {/* Background Decor */}
      <div className={styles.bgDecor1} />
      <div className={styles.bgDecor2} />

      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logoContainer}>
            <div className={styles.logoIcon}>
              <Shield />
            </div>
            <h1 className={styles.logoText}>PatentSense</h1>
          </div>
          <p className={styles.subtitle}>아이디어 검증 AI 에이전트</p>
        </div>

        <div className={styles.sidebarContent}>
          <section>
            <div className={styles.sectionHeader}>
              <Lightbulb />
              <h2 className={styles.sectionTitle}>아이디어 구체화</h2>
            </div>

            <div className={styles.inputGroup}>
              <InputField
                label="발명의 명칭"
                value={formData.title}
                onChange={(val: string) => setFormData({ ...formData, title: val })}
                placeholder="예: 스마트 화분 제어 시스템"
              />

              <InputField
                label="해결하려는 과제 (배경)"
                value={formData.background}
                onChange={(val: string) => setFormData({ ...formData, background: val })}
                placeholder="기존 기술의 어떤 문제점을 해결하나요?"
                rows={2}
              />

              <InputField
                label="구체적 내용 (수단)"
                value={formData.details}
                onChange={(val: string) => setFormData({ ...formData, details: val })}
                placeholder="아이디어의 핵심 구성 요소를 적어주세요."
                rows={4}
                required
              />

              <InputField
                label="기대 효과"
                value={formData.effect}
                onChange={(val: string) => setFormData({ ...formData, effect: val })}
                placeholder="도입 시 예상되는 장점은 무엇인가요?"
                rows={2}
              />
            </div>
          </section>

          <div className={styles.actionButtons}>
            {appState === 'idle' ? (
              <button
                onClick={handleSubmit}
                disabled={!isFormValid}
                className={styles.submitBtn}
              >
                검증 시작하기 <ArrowRight />
              </button>
            ) : (
              <button
                onClick={resetForm}
                className={styles.resetBtn}
              >
                새 아이디어 작성
              </button>
            )}
          </div>
        </div>

        <div className={styles.historySection}>
          <div className={styles.historyHeader}>
            <span>최근 내역</span>
            <span>{history.length}</span>
          </div>
          <div className={styles.historyList}>
            {history.length === 0 ? (
              <div className={styles.emptyHistory}>저장된 내역이 없습니다.</div>
            ) : (
              history.map(item => (
                <div key={item.id} className={styles.historyItem} onClick={() => loadHistoryItem(item)}>
                  <div className={styles.historyItemTitle}>{item.formData.title || '제목 없음'}</div>
                  <div className={styles.historyItemDate}>
                    {new Date(item.timestamp).toLocaleString()}
                  </div>
                  <button className={styles.historyItemDelete} onClick={(e) => deleteHistoryItem(e, item.id)}>
                    <XCircle />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className={styles.actualFooter}>
          <p>데이터는 브라우저의 로컬스토리지에 저장됩니다</p>
          <p>이 성과는 2026년도 과학기술정보통신부의 재원으로 정보통신기획평가원의 지원을 받아 수행된 결과물임 (IITP-2026-AI·SW마에스트로)</p>
          <p>© 2026 PatentSense. All rights reserved.</p>
        </div>
      </aside>

      {/* Main Canvas */}
      <main className={styles.mainCanvas}>
        <div className={styles.canvasContent}>
          {appState === 'idle' && <IdleView />}
          {appState === 'processing' && <ProcessingView step={step} steps={STEPS} />}
          {appState === 'result' && <ResultView result={result} logs={logs} />}
        </div>
      </main>
    </div>
  );
}

// --- Sub-components ---

function InputField({ label, value, onChange, placeholder, rows = 1, required = false }: any) {
  return (
    <div className={styles.inputField}>
      <label className={styles.label}>
        {label} {required && <span className={styles.required}>*</span>}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className={styles.textarea}
      />
    </div>
  );
}

function IdleView() {
  return (
    <div className={styles.idleContainer}>
      <div className={styles.idleIconBox}>
        <Sparkles />
      </div>
      <div>
        <h2 className={styles.idleTitle}>아이디어의 가치를 확인하세요</h2>
        <p className={styles.idleDesc}>
          좌측 패널에 작성하신 내용은 KIPRIS 특허 DB와 실시간으로 대조되어 상세 리포트로 생성됩니다.
        </p>
      </div>
    </div>
  );
}

function ProcessingView({ step, steps }: any) {
  return (
    <div className={styles.procContainer}>
      <div className={styles.procBox}>
        <Loader2 className={styles.spinner} />
        <div className={styles.stepsList}>
          {steps.map((s: string, i: number) => (
            <div key={i} className={`${styles.stepItem} ${i === step ? styles.stepActive : (i > step ? styles.stepInactive : '')}`}>
              <div className={`${styles.stepCircle} ${i <= step ? styles.stepCircleDone : styles.stepCirclePending}`}>
                {i < step ? <CheckCircle /> : <span className={styles.stepNumber}>{i + 1}</span>}
              </div>
              <span className={`${styles.stepText} ${i === step ? styles.stepTextActive : styles.stepTextInactive}`}>
                {s} {i <= step ? '중...' : '대기'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ResultView({ result, logs }: { result: any, logs: LogEntry[] }) {
  if (!result) return null;

  // Compute highest similarity from top_patents if available
  let highestSim = 0;
  if (result.top_patents && result.top_patents.length > 0) {
    highestSim = Math.max(...result.top_patents.map((p: any) => p.similarity_score || 0));
  }

  const riskColorClass = highestSim >= 80 ? 'text-red-500' : (highestSim >= 60 ? 'text-amber-500' : 'text-green-500');
  const riskLabel = highestSim >= 80 ? 'High Risk' : (highestSim >= 60 ? 'Medium Risk' : 'Low Risk');

  const reportParts = result.report ? result.report.split('<!-- CARD_BREAK -->') : [];

  return (
    <div className={styles.resultContainer}>
      {/* Header Card */}


      {reportParts.map((part: string, index: number) => (
        <div key={index} className={styles.reportBox}>
          <div className={styles.markdown}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
              {part}
            </ReactMarkdown>
          </div>
        </div>
      ))}

      <div className={styles.disclaimer}>
        <Info />
        <p className={styles.disclaimerText}>
          본 에이전트의 분석 결과는 KIPRIS 공개 데이터를 바탕으로 한 참고 자료이며, 실제 출원 및 법적 대응 시에는 반드시 전문 변리사와 상담하십시오.
        </p>
      </div>

      {/* Optional: Raw Logs Expander if needed, omitted for UI cleanliness */}
    </div>
  );
}
