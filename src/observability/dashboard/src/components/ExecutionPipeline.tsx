import { useEffect, useState } from 'react';
import { ExecutionStep } from '@/types/metrics';
import { useWebSocketMessages } from '@/hooks/useWebSocket';
import './ExecutionPipeline.css';

const STAGES = [
  { id: 'data', label: 'Data Ingestion', icon: '📊' },
  { id: 'signal', label: 'Signal Generation', icon: '🎯' },
  { id: 'risk', label: 'Risk Check', icon: '🛡️' },
  { id: 'execution', label: 'Order Execution', icon: '⚡' },
  { id: 'confirmation', label: 'Confirmation', icon: '✓' },
] as const;

export function ExecutionPipeline() {
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [wsStep, loading] = useWebSocketMessages<ExecutionStep>('execution', {} as ExecutionStep);

  useEffect(() => {
    if (!loading && wsStep.stage) {
      setSteps((prev) => {
        const updated = [...prev];
        const index = updated.findIndex((s) => s.stage === wsStep.stage);
        if (index >= 0) {
          updated[index] = wsStep;
        } else {
          updated.push(wsStep);
        }
        return updated.slice(-20);
      });
    }
  }, [wsStep, loading]);

  const getStepStatus = (stageId: string): ExecutionStep | undefined => {
    return steps.find((s) => s.stage === stageId);
  };

  const getStatusClass = (status?: string): string => {
    switch (status) {
      case 'success':
        return 'status-success';
      case 'error':
        return 'status-error';
      case 'processing':
        return 'status-processing';
      default:
        return 'status-pending';
    }
  };

  return (
    <div className="execution-pipeline">
      <h2>Execution Pipeline</h2>
      <div className="pipeline-stages">
        {STAGES.map((stage, index) => {
          const step = getStepStatus(stage.id);
          const statusClass = getStatusClass(step?.status);

          return (
            <div key={stage.id} className="pipeline-stage-wrapper">
              <div className={`pipeline-stage ${statusClass}`}>
                <div className="stage-icon">{stage.icon}</div>
                <div className="stage-label">{stage.label}</div>
                {step && (
                  <div className="stage-info">
                    <div className="stage-duration">
                      {step.duration_ms ? `${step.duration_ms}ms` : '-'}
                    </div>
                    {step.error && (
                      <div className="stage-error" title={step.error}>
                        Error
                      </div>
                    )}
                  </div>
                )}
              </div>
              {index < STAGES.length - 1 && (
                <div className={`pipeline-arrow ${statusClass}`}>→</div>
              )}
            </div>
          );
        })}
      </div>
      <div className="pipeline-details">
        {steps.slice(-5).reverse().map((step, idx) => (
          <div key={`${step.stage}-${step.timestamp}`} className="step-detail">
            <span className={`step-status ${getStatusClass(step.status)}`}>●</span>
            <span className="step-stage">{step.stage}</span>
            <span className="step-time">
              {new Date(step.timestamp).toLocaleTimeString()}
            </span>
            {step.details && <span className="step-details">{step.details}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
