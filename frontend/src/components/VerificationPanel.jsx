import { useEffect, useState } from "react";
import UploadCard from "./UploadCard";

function formatLongValue(value) {
  if (!value) return "";
  return value.match(/.{1,40}/g)?.join("\n") || value;
}

function VerificationPanel({ apiBase, seedImageBase64 = "", onSeedConsumed = () => {} }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!seedImageBase64) return;

    const raw = atob(seedImageBase64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) {
      arr[i] = raw.charCodeAt(i);
    }

    const blob = new Blob([arr], { type: "image/png" });
    const seeded = new File([blob], "signed_image.png", { type: "image/png" });
    setFile(seeded);
    onSeedConsumed();
  }, [seedImageBase64, onSeedConsumed]);

  const verifyImage = async () => {
    if (!file) return;

    setBusy(true);
    setError("");
    setResult(null);

    const data = new FormData();
    data.append("image", file);

    try {
      const response = await fetch(`${apiBase}/verify-image`, {
        method: "POST",
        body: data,
      });

      if (!response.ok) {
        throw new Error("Verification failed");
      }

      const payload = await response.json();
      setResult(payload);
    } catch (err) {
      setError(err.message || "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel-card verify-panel">
      <h2>Verification Panel</h2>
      <UploadCard
        label="Upload Image to Verify"
        file={file}
        onFileSelected={setFile}
        onSubmit={verifyImage}
        busy={busy}
        buttonText="Verify Image"
      />

      <p className="muted-note">
        Tip: upload the exact downloaded <strong>signed_image.png</strong> (not screenshot / edited / recompressed copy).
      </p>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <div className={`result-card ${result.is_valid ? "ok" : "bad"}`}>
          <h3>{result.message}</h3>
          <p><strong>Extracted Signature:</strong></p>
          <pre className="mono-box small">{formatLongValue(result.extracted_signature) || "Not found"}</pre>
          <p><strong>Recomputed Hash (hash used for signature verification):</strong></p>
          <pre className="mono-box small">{formatLongValue(result.recomputed_hash)}</pre>
          <span className="status-badge">{result.is_valid ? "Authentic" : "Tampered"}</span>

          {result.comparison_details && (
            <div className="verification-flow">
              <h4>How Comparison Is Performed</h4>
              <p><strong>Algorithm:</strong> {result.comparison_details.algorithm}</p>
              <pre className="mono-box small">{result.comparison_details.comparison_rule}</pre>
              <div className="flow-steps">
                {(result.comparison_details.checks || []).map((item, index) => (
                  <p key={`${item}-${index}`}>[{index + 1}] {item}</p>
                ))}
              </div>
              <p>
                <strong>Signature bytes:</strong> {result.comparison_details.extracted_signature_length_bytes} |
                <strong> Hash length:</strong> {result.comparison_details.recomputed_hash_length}
              </p>
              <p><strong>Comparison result:</strong> {result.comparison_details.result}</p>
              {!result.is_valid && (
                <p className="muted-note">
                  If this should be authentic, try "Verify this exact signed output" from the Signing page. Failures are
                  commonly caused by selecting the wrong file, format conversion, or signing/verification key mismatch.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default VerificationPanel;
