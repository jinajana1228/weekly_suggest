export default function DisclaimerPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-2xl font-semibold text-text-primary mb-2">면책 고지</h1>
      <p className="text-sm text-text-muted mb-8">Disclaimer</p>

      <div className="space-y-6 text-sm text-text-secondary leading-relaxed">
        <section>
          <h2 className="text-base font-medium text-text-primary mb-2">1. 서비스 성격</h2>
          <p>
            본 서비스(Weekly Suggest)는 미국 상장 주식에 대한 정보 및 분석을 제공하는 목적으로 운영됩니다.
            본 서비스는 금융투자업 인가를 받은 투자자문업자가 아니며, 제공되는 모든 콘텐츠는
            투자 권유 또는 투자 자문에 해당하지 않습니다.
          </p>
        </section>

        <section>
          <h2 className="text-base font-medium text-text-primary mb-2">2. 투자 결정 책임</h2>
          <p>
            본 서비스에서 제공하는 모든 분석, 수치, 의견, 서술은 투자자의 독립적인 판단을 위한
            참고 자료입니다. 최종 투자 결정 및 그에 따른 손익은 전적으로 투자자 본인의 책임입니다.
            본 서비스는 투자 결과에 대한 어떠한 법적 책임도 지지 않습니다.
          </p>
        </section>

        <section>
          <h2 className="text-base font-medium text-text-primary mb-2">3. 데이터 정확성</h2>
          <p>
            제공되는 재무 데이터, 가격 정보, 컨센서스 추정치는 공개된 외부 데이터 소스를 기반으로 하며,
            실시간 정보가 아닙니다. 데이터의 정확성, 완전성, 최신성을 보장하지 않으며,
            데이터 오류나 누락으로 인한 손해에 대해 책임을 지지 않습니다.
          </p>
        </section>

        <section>
          <h2 className="text-base font-medium text-text-primary mb-2">4. 관심 가격 구간</h2>
          <p>
            본 서비스에서 제시하는 '관심 가격 구간'은 목표주가(Target Price)가 아닙니다.
            이는 특정 밸류에이션 멀티플 수렴 시점의 이론적 가격 범위를 조건부로 제시한 것이며,
            해당 가격에서의 매수를 권유하거나 특정 수익률을 약속하는 것이 아닙니다.
          </p>
        </section>

        <section>
          <h2 className="text-base font-medium text-text-primary mb-2">5. 과거 데이터</h2>
          <p>
            과거의 주가 움직임, 재무 실적, 밸류에이션 패턴은 미래의 결과를 보장하지 않습니다.
            투자에는 원금 손실의 위험이 포함됩니다.
          </p>
        </section>

        <section>
          <h2 className="text-base font-medium text-text-primary mb-2">6. AI 생성 콘텐츠</h2>
          <p>
            일부 분석 서술은 AI 언어 모델(Claude)을 활용하여 생성되며, 전문 검토자의 검수 과정을 거칩니다.
            그러나 AI 생성 콘텐츠의 특성상 오류나 부정확한 내용이 포함될 수 있습니다.
          </p>
        </section>

        <div className="pt-6 border-t border-border-default">
          <p className="text-xs text-text-muted">최종 업데이트: 2025년 3월</p>
        </div>
      </div>
    </div>
  );
}
