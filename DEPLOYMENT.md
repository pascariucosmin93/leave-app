{{- /* Trivy HTML report template (static, self-contained) */ -}}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Trivy Report - {{ .ArtifactName }}</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,Helvetica,Arial,sans-serif;line-height:1.4;margin:16px;color:#222}
    h1{font-size:20px;margin:0 0 12px}
    .meta{color:#666;font-size:12px;margin-bottom:16px}
    table{border-collapse:collapse;width:100%}
    th,td{border:1px solid #e5e7eb;padding:8px;text-align:left;vertical-align:top}
    th{background:#f8fafc}
    .sev{font-weight:600;padding:2px 6px;border-radius:4px;display:inline-block}
    .CRITICAL{background:#fee2e2;color:#991b1b}
    .HIGH{background:#ffe4e6;color:#9f1239}
    .MEDIUM{background:#fef9c3;color:#713f12}
    .LOW{background:#dcfce7;color:#14532d}
    .UNKNOWN{background:#e5e7eb;color:#334155}
    details{margin-top:6px}
    summary{cursor:pointer;color:#2563eb}
    code{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;background:#f3f4f6;padding:2px 4px;border-radius:3px}
  </style>
  </head>
  <body>
    <h1>Trivy Vulnerability Report</h1>
    <div class="meta">
      Target: <strong>{{ .ArtifactName }}</strong><br/>
      Generated at: {{ now }}<br/>
      Trivy Version: {{ .TrivyVersion }}
    </div>

    {{- if not .Results }}
      <p>No results.</p>
    {{- end }}

    {{- range .Results }}
      <h2>{{ .Target }} <small>({{ .Type }})</small></h2>
      {{- if not .Vulnerabilities }}
        <p>Clean (no vulnerabilities detected).</p>
      {{- else }}
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>ID</th>
              <th>Pkg</th>
              <th>Installed</th>
              <th>Fixed</th>
              <th>Title</th>
            </tr>
          </thead>
          <tbody>
          {{- range .Vulnerabilities }}
            <tr>
              <td><span class="sev {{ .Severity }}">{{ .Severity }}</span></td>
              <td><a href="{{ .PrimaryURL }}" target="_blank" rel="noreferrer">{{ .VulnerabilityID }}</a></td>
              <td>{{ .PkgName }}</td>
              <td><code>{{ .InstalledVersion }}</code></td>
              <td><code>{{ .FixedVersion }}</code></td>
              <td>
                {{ .Title }}
                {{- if .Description }}
                <details>
                  <summary>Details</summary>
                  <pre>{{ .Description }}</pre>
                </details>
                {{- end }}
              </td>
            </tr>
          {{- end }}
          </tbody>
        </table>
      {{- end }}
    {{- end }}
  </body>
</html>
