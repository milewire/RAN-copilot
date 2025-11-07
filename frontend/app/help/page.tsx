'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Info, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'

interface KPIThreshold {
  name: string
  description: string
  idealValue: string
  threshold: string
  unit: string
  category: string
}

const KPI_THRESHOLDS: KPIThreshold[] = [
  {
    name: "RRC_Setup_Success_Rate",
    description: "Radio Resource Control connection setup success rate",
    idealValue: "≥ 95%",
    threshold: "Minimum: 95%",
    unit: "%",
    category: "Connection Management"
  },
  {
    name: "ERAB_Setup_Success_Rate",
    description: "E-UTRAN Radio Access Bearer setup success rate",
    idealValue: "≥ 98%",
    threshold: "Minimum: 98%",
    unit: "%",
    category: "Connection Management"
  },
  {
    name: "PRB_Utilization_Avg",
    description: "Average Physical Resource Block utilization",
    idealValue: "< 70%",
    threshold: "Maximum: 70%",
    unit: "%",
    category: "Resource Utilization"
  },
  {
    name: "PRB_Utilization_P95",
    description: "95th percentile PRB utilization (peak load)",
    idealValue: "< 85%",
    threshold: "Maximum: 85%",
    unit: "%",
    category: "Resource Utilization"
  },
  {
    name: "SINR_Avg",
    description: "Average Signal-to-Interference-plus-Noise Ratio",
    idealValue: "> 5 dB",
    threshold: "Minimum: 5 dB",
    unit: "dB",
    category: "Radio Quality"
  },
  {
    name: "SINR_P10",
    description: "10th percentile SINR (worst-case coverage)",
    idealValue: "> 0 dB",
    threshold: "Minimum: 0 dB",
    unit: "dB",
    category: "Radio Quality"
  },
  {
    name: "BLER_P95",
    description: "95th percentile Block Error Rate",
    idealValue: "< 10%",
    threshold: "Maximum: 10%",
    unit: "%",
    category: "Error Rates"
  },
  {
    name: "Paging_Success_Rate",
    description: "Paging procedure success rate",
    idealValue: "≥ 95%",
    threshold: "Minimum: 95%",
    unit: "%",
    category: "Core Network"
  },
  {
    name: "S1_Setup_Failure_Rate",
    description: "S1 interface setup failure rate",
    idealValue: "< 1%",
    threshold: "Maximum: 1%",
    unit: "%",
    category: "Core Network"
  },
  {
    name: "Cell_Availability",
    description: "Cell availability percentage",
    idealValue: "≥ 99%",
    threshold: "Minimum: 99%",
    unit: "%",
    category: "Availability"
  }
]

const ADDITIONAL_KPIS = [
  {
    name: "RRC_Setup_Attempts",
    description: "Number of RRC connection establishment attempts",
    category: "Connection Management"
  },
  {
    name: "RRC_Setup_Success",
    description: "Number of successful RRC connection establishments",
    category: "Connection Management"
  },
  {
    name: "RRC_Connections",
    description: "Current number of RRC connections",
    category: "Connection Management"
  },
  {
    name: "ERAB_Setup_Attempts",
    description: "Number of ERAB establishment attempts",
    category: "Connection Management"
  },
  {
    name: "ERAB_Setup_Success",
    description: "Number of successful ERAB establishments",
    category: "Connection Management"
  },
  {
    name: "ERAB_Connections",
    description: "Current number of active ERAB connections",
    category: "Connection Management"
  },
  {
    name: "SINR_PUSCH",
    description: "SINR on Physical Uplink Shared Channel",
    category: "Radio Quality"
  },
  {
    name: "BLER_DL",
    description: "Downlink Block Error Rate",
    category: "Radio Quality"
  },
  {
    name: "Downlink_Throughput",
    description: "Downlink data throughput (bits per second)",
    category: "Throughput"
  },
  {
    name: "Uplink_Throughput",
    description: "Uplink data throughput (bits per second)",
    category: "Throughput"
  },
  {
    name: "Handover_Success_Rate",
    description: "Success rate of handover procedures",
    category: "Mobility"
  }
]

const categories = Array.from(new Set([...KPI_THRESHOLDS, ...ADDITIONAL_KPIS].map(k => k.category)))

export default function HelpPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">KPI Parameters Help</h1>
        <p className="text-muted-foreground">
          Reference guide for KPI parameters, ideal values, and thresholds
        </p>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>About KPI Thresholds</AlertTitle>
        <AlertDescription>
          The application monitors KPIs against these thresholds to detect anomalies and identify root causes.
          Values outside these thresholds trigger alerts and contribute to root cause analysis.
        </AlertDescription>
      </Alert>

      {categories.map((category) => {
        const thresholdKPIs = KPI_THRESHOLDS.filter(k => k.category === category)
        const additionalKPIs = ADDITIONAL_KPIS.filter(k => k.category === category)
        
        return (
          <Card key={category}>
            <CardHeader>
              <CardTitle>{category}</CardTitle>
              <CardDescription>KPI parameters in this category</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* KPIs with Thresholds */}
              {thresholdKPIs.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-3 text-muted-foreground">
                    KPIs with Defined Thresholds
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {thresholdKPIs.map((kpi) => (
                      <div key={kpi.name} className="p-4 border rounded-lg space-y-2">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-semibold text-sm">{kpi.name}</h4>
                            <p className="text-xs text-muted-foreground mt-1">{kpi.description}</p>
                          </div>
                          <div className="ml-4 text-right">
                            <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
                              <CheckCircle2 className="h-4 w-4" />
                              <span className="text-sm font-medium">{kpi.idealValue}</span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">{kpi.unit}</p>
                          </div>
                        </div>
                        <div className="pt-2 border-t">
                          <p className="text-xs">
                            <span className="font-medium">Threshold:</span> {kpi.threshold}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Additional KPIs without thresholds */}
              {additionalKPIs.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold mb-3 text-muted-foreground">
                    Additional Monitored KPIs
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {additionalKPIs.map((kpi) => (
                      <div key={kpi.name} className="p-4 border rounded-lg">
                        <h4 className="font-semibold text-sm">{kpi.name}</h4>
                        <p className="text-xs text-muted-foreground mt-1">{kpi.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}

      {/* Root Cause Classifications */}
      <Card>
        <CardHeader>
          <CardTitle>Root Cause Classifications</CardTitle>
          <CardDescription>How KPIs are used to identify root causes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">Transport/TIMING Fault</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: S1 failure + (RRC or ERAB anomalies)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: S1_Setup_Failure_Rate, RRC_Setup_Success_Rate, ERAB_Setup_Success_Rate
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">Microwave ACM Fade</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: S1 failure + PRB anomalies
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: S1_Setup_Failure_Rate, PRB_Utilization_Avg
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">TDD Frame Misalignment</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: SINR anomalies + BLER anomalies (without PRB issues)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: SINR_Avg, SINR_P10, BLER_P95
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">RF Interference / Sector Overshoot</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: SINR anomalies + BLER anomalies + PRB anomalies
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: SINR_Avg, BLER_P95, PRB_Utilization_Avg
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">Congestion</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: PRB anomalies + RRC anomalies (without SINR issues)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: PRB_Utilization_Avg, RRC_Setup_Success_Rate
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">RF Quality Degradation</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: SINR anomalies + BLER anomalies
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: SINR_Avg, BLER_P95
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">Parameter Mismatch</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: RRC or ERAB anomalies (without S1 or PRB issues)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: RRC_Setup_Success_Rate, ERAB_Setup_Success_Rate
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">New-Site Integration Issue</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: Paging anomalies + RRC anomalies
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: Paging_Success_Rate, RRC_Setup_Success_Rate
              </p>
            </div>

            <div className="p-4 border rounded-lg">
              <h4 className="font-semibold mb-2">CPE-Specific Issue</h4>
              <p className="text-sm text-muted-foreground">
                Detected when: BLER anomalies (without SINR issues)
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Key KPIs: BLER_P95
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Severity Levels */}
      <Card>
        <CardHeader>
          <CardTitle>Severity Levels</CardTitle>
          <CardDescription>How severity is determined</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 border rounded-lg">
              <XCircle className="h-5 w-5 text-destructive" />
              <div>
                <p className="font-semibold">High Severity</p>
                <p className="text-sm text-muted-foreground">
                  Critical performance issues requiring immediate attention. 
                  KPI values are significantly outside thresholds (&gt;20% deviation).
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 border rounded-lg">
              <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              <div>
                <p className="font-semibold">Medium Severity</p>
                <p className="text-sm text-muted-foreground">
                  Moderate performance degradation. KPI values are outside thresholds 
                  but within 20% of threshold values. Monitoring recommended.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 border rounded-lg">
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              <div>
                <p className="font-semibold">Low Severity</p>
                <p className="text-sm text-muted-foreground">
                  System operating within normal parameters. All KPIs are within 
                  acceptable thresholds. Minor observations may be present.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

