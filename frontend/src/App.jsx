import { useEffect, useMemo, useState } from "react";
import StepCard from "./components/StepCard";
import UploadCard from "./components/UploadCard";
import VerificationPanel from "./components/VerificationPanel";

const TOTAL_STEPS = 5;

function formatHash(value) {
  if (!value) return "";
  return value.match(/.{1,32}/g)?.join("\n") || value;
}

function formatMatrix(matrix) {
  if (!Array.isArray(matrix) || matrix.length === 0) return [];

  return matrix.map((row) =>
    row.map((cell) => {
      const n = Number(cell);
      if (Number.isNaN(n)) return String(cell);
      if (Math.abs(n) >= 100) return n.toFixed(1);
      if (Math.abs(n) >= 1) return n.toFixed(3);
      return n.toFixed(4);
    })
  );
}

function MatrixTable({ matrix, mode = "plain", dctPositions = [], referenceMatrix = null, epsilon = 0.001 }) {
  const rows = formatMatrix(matrix);
  if (!rows.length) {
    return <p className="muted-note">Matrix unavailable.</p>;
  }

  const isDctPosition = (rIdx, cIdx) =>
    dctPositions.some((pos) => pos[0] === rIdx && pos[1] === cIdx);

  const cellClass = (rawValue, rIdx, cIdx) => {
    const value = Number(rawValue);

    if (mode === "dct") {
      return isDctPosition(rIdx, cIdx) ? "matrix-cell-green" : "";
    }

    if (mode === "dct-after") {
      const ref = Number(referenceMatrix?.[rIdx]?.[cIdx]);
      const changed = !Number.isNaN(ref) && Math.abs(value - ref) > epsilon;
      if (changed) return "matrix-cell-red";
      return isDctPosition(rIdx, cIdx) ? "matrix-cell-green" : "";
    }

    if (mode === "delta") {
      if (Math.abs(value) <= epsilon) return "matrix-cell-blue";
      return "matrix-cell-red";
    }

    return "";
  };

  return (
    <div className="matrix-table-wrap">
      <table className="matrix-table">
        <tbody>
          {rows.map((row, rIdx) => (
            <tr key={`r-${rIdx}`}>
              {row.map((value, cIdx) => (
                <td
                  key={`c-${rIdx}-${cIdx}`}
                  className={cellClass(matrix[rIdx][cIdx], rIdx, cIdx)}
                >
                  {value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const apiBase = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const [view, setView] = useState("home");
  const [file, setFile] = useState(null);
  const [signResult, setSignResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showFullSignature, setShowFullSignature] = useState(false);
  const [logs, setLogs] = useState([]);
  const [inputPreviewUrl, setInputPreviewUrl] = useState("");
  const [showStep4Explain, setShowStep4Explain] = useState(false);
  const [verifySeedBase64, setVerifySeedBase64] = useState("");

  const signedImageUrl = useMemo(() => {
    if (!signResult?.signed_image) return "";
    return `data:image/png;base64,${signResult.signed_image}`;
  }, [signResult]);

  useEffect(() => {
    if (!file) {
      setInputPreviewUrl("");
      return undefined;
    }

    const nextUrl = URL.createObjectURL(file);
    setInputPreviewUrl(nextUrl);

    return () => {
      URL.revokeObjectURL(nextUrl);
    };
  }, [file]);

  const currentStep = signResult ? TOTAL_STEPS : file ? 1 : 0;
  const embeddingDebug = signResult?.embedding_debug;
  const dctPositions = embeddingDebug?.dct_positions || [];
  const blockRows = embeddingDebug?.block_grid?.rows || 0;
  const blockCols = embeddingDebug?.block_grid?.cols || 0;
  const selectedBlockRow =
    embeddingDebug?.selected_block_explanation?.block_row ??
    embeddingDebug?.selected_block_meta?.block_row ??
    null;
  const selectedBlockCol =
    embeddingDebug?.selected_block_explanation?.block_col ??
    embeddingDebug?.selected_block_meta?.block_col ??
    null;
  const hasSelectedBlock = selectedBlockRow !== null && selectedBlockCol !== null;

  const stepStatusLabel = {
    0: "Waiting for Upload",
    1: "Image Loaded",
    2: "Hash Generated",
    3: "Signature Created",
    4: "Signature Embedded",
    5: "Signed Image Ready",
  };

  const copyHash = async () => {
    if (signResult?.hash) {
      await navigator.clipboard.writeText(signResult.hash);
      setLogs((prev) => [...prev, "Hash copied to clipboard"]);
    }
  };

  const signImage = async () => {
    if (!file) return;

    setBusy(true);
    setError("");
    setSignResult(null);
    setLogs(["Preparing upload..."]);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch(`${apiBase}/sign-image`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Signing request failed");
      }

      const payload = await response.json();
      setSignResult(payload);
      setLogs(payload.debug_steps || []);
    } catch (err) {
      setError(err.message || "Request failed");
      setLogs((prev) => [...prev, "Error while processing image"]);
    } finally {
      setBusy(false);
    }
  };

  if (view === "home") {
    return (
      <main className="app-shell">
        <header className="top-banner">
          <h1>Tamper-Evident Image Authentication System</h1>
          <p>Choose what you want to do first, then continue in a dedicated page.</p>
        </header>
        <section className="mode-choice-grid">
          <button className="mode-choice-card" onClick={() => setView("sign")}>Sign / Upload Image</button>
          <button className="mode-choice-card" onClick={() => setView("verify")}>Verify Signed Image</button>
        </section>
      </main>
    );
  }

  if (view === "verify") {
    return (
      <main className="app-shell">
        <header className="top-banner compact">
          <div className="row-between">
            <h1>Verification Page</h1>
            <button className="mini-button" onClick={() => setView("home")}>Back</button>
          </div>
          <p>Upload a signed image, extract signature, recompute hash, and inspect comparison logic.</p>
        </header>
        <section className="single-page-panel">
          <VerificationPanel
            apiBase={apiBase}
            seedImageBase64={verifySeedBase64}
            onSeedConsumed={() => setVerifySeedBase64("")}
          />
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="top-banner compact">
        <div className="row-between">
          <h1>Signing Page</h1>
          <button className="mini-button" onClick={() => setView("home")}>Back</button>
        </div>
        <p>Upload image, download signed image, then inspect the full step-by-step pipeline below.</p>
      </header>

      <section className="single-page-panel">
        <UploadCard
          label="Upload Image"
          file={file}
          onFileSelected={setFile}
          onSubmit={signImage}
          busy={busy}
          buttonText="Sign and Embed"
        />

        {signResult?.signed_image && (
          <div className="panel-card">
            <h3>Download Signed Image</h3>
            <img src={signedImageUrl} alt="Signed output" className="image-preview" />
            <a className="action-button inline" href={signedImageUrl} download="signed_image.png">
              Download signed image
            </a>
            <button
              className="mini-button"
              onClick={() => {
                setVerifySeedBase64(signResult.signed_image);
                setView("verify");
              }}
            >
              Verify this exact signed output
            </button>
          </div>
        )}

        <section className="progress-panel">
          <h3>Step Progress</h3>
          <div className="step-progress-track">
            <div
              className="step-progress-fill"
              style={{ width: `${(currentStep / TOTAL_STEPS) * 100}%` }}
            />
          </div>
          <p>
            Step {currentStep} of {TOTAL_STEPS} - {stepStatusLabel[currentStep]}
          </p>
        </section>

        <div className="panel-card logs-panel">
          <h3>Processing Logs</h3>
          {logs.length === 0 && <p>No logs yet.</p>}
          {logs.map((log, index) => (
            <p key={`${log}-${index}`}>[{index + 1}] {log}</p>
          ))}
        </div>

        <div className="step-sequence">
          <StepCard
            title="Step 1: Image Loaded"
            explain="The selected file is decoded into pixel data for downstream processing."
            active={currentStep >= 1}
          >
            {file ? (
              <img src={inputPreviewUrl} alt="Raw input" className="image-preview" />
            ) : (
              <p>Upload an image to begin.</p>
            )}
          </StepCard>

          <StepCard
            title="Step 2: Hash Generation"
            explain="A robust image hash is transformed with SHA-256 for signing and verification."
            active={currentStep >= 2}
          >
            <p className="step-context">Generate a unique fingerprint of the image.</p>
            {busy && <div className="loader">Generating hash...</div>}
            {signResult?.hash && (
              <>
                <pre className="mono-box">{formatHash(signResult.hash)}</pre>
                <button className="mini-button" onClick={copyHash}>Copy hash</button>
              </>
            )}
          </StepCard>

          <StepCard
            title="Step 3: Signature Generation"
            explain="The hash is signed using ECDSA, producing a digital signature."
            active={currentStep >= 3}
          >
            <p className="step-context">Encrypt the hash to prove ownership.</p>
            {busy && <div className="loader">Creating digital signature...</div>}
            {signResult?.signature && (
              <>
                <p className="label">Digital Signature</p>
                <pre className="mono-box">
                  {showFullSignature
                    ? signResult.signature
                    : `${signResult.signature_preview}...`}
                </pre>
                <button
                  className="mini-button"
                  onClick={() => setShowFullSignature((prev) => !prev)}
                >
                  {showFullSignature ? "Show less" : "Show full signature"}
                </button>
              </>
            )}
          </StepCard>

          <StepCard
            title="Step 4: Embedding Visualization"
            explain="Embedding signature into frequency domain (DCT)."
            active={currentStep >= 4}
          >
            <p className="step-context">Hide the signature inside image frequency components.</p>
            {busy && <div className="loader">Embedding into DCT coefficients...</div>}
            <p>Embedding signature into frequency domain (DCT)</p>

            <button className="mini-button" onClick={() => setShowStep4Explain((prev) => !prev)}>
              What is happening here?
            </button>
            {showStep4Explain && (
              <p className="explain-inline">
                Each bit of the signature is embedded by modifying selected DCT coefficients. These changes are
                small but structured.
              </p>
            )}

            {embeddingDebug && (
              <div className="dct-debug-wrap">
                <div className="panel-subtle">
                  <p>
                    <strong>Payload bits:</strong> {embeddingDebug.payload_bit_count}
                  </p>
                  <p>
                    <strong>Image split:</strong> {blockRows} x {blockCols} blocks of size 8 x 8 pixels
                  </p>
                  <p>
                    <strong>Selected debug block:</strong>{" "}
                    {hasSelectedBlock ? `(${selectedBlockRow}, ${selectedBlockCol})` : "Not available"}
                  </p>
                  <p>
                    <strong>DCT positions used:</strong>{" "}
                    {dctPositions.map((pos) => `(${pos[0]},${pos[1]})`).join(" ")}
                  </p>
                  <p className="muted-note">Mid-frequency coefficients are selected to balance invisibility and robustness.</p>
                  <p>
                    <strong>Quantization step:</strong> {embeddingDebug.quantization_step}
                  </p>
                  <p className="muted-note">Controls embedding strength: higher = more robust, lower = less visible.</p>
                  <p>
                    <strong>Modified operations:</strong> {embeddingDebug.modified_operations_count} / {embeddingDebug.total_operations_scanned}
                  </p>
                </div>

                <div className="flow-row" aria-hidden>
                  <span>Pixel Block</span>
                  <span>-&gt;</span>
                  <span>DCT</span>
                  <span>-&gt;</span>
                  <span>Modify</span>
                  <span>-&gt;</span>
                  <span>Inverse DCT</span>
                  <span>-&gt;</span>
                  <span>New Pixels</span>
                </div>

                {embeddingDebug.selected_block_before && embeddingDebug.selected_block_after && (
                  <div className="section-stack">
                    <p className="label">Selected 8x8 Pixel Block</p>
                    <p className="muted-note">This is a small 8x8 region extracted from the image</p>

                    <div className="matrix-grid triple">
                      <div>
                        <p className="label">Before embedding</p>
                        <MatrixTable matrix={embeddingDebug.selected_block_before} mode="plain" />
                      </div>
                      <div>
                        <p className="label">After embedding</p>
                        <MatrixTable matrix={embeddingDebug.selected_block_after} mode="plain" />
                      </div>
                      <div>
                        <p className="label">Delta (after - before)</p>
                        <MatrixTable matrix={embeddingDebug.selected_block_delta} mode="delta" />
                      </div>
                    </div>

                    <p className="section-divider">Transformation: Spatial Domain -&gt; Frequency Domain using DCT</p>

                    <p className="label">DCT Block (Before Embedding)</p>
                    <p className="muted-note">
                      DCT converts pixel values into frequency components. The data is the same but represented differently.
                    </p>
                    <div className="matrix-grid">
                      <div>
                        <MatrixTable matrix={embeddingDebug.selected_dct_before} mode="dct" dctPositions={dctPositions} />
                      </div>
                    </div>

                    <p className="label">Embedding positions</p>
                    <p className="muted-note">Mid-frequency coefficients are selected to balance invisibility and robustness.</p>

                    <p className="label">DCT Block (After Embedding)</p>
                    <div className="matrix-grid">
                      <div>
                        <MatrixTable
                          matrix={embeddingDebug.selected_dct_after}
                          mode="dct-after"
                          dctPositions={dctPositions}
                          referenceMatrix={embeddingDebug.selected_dct_before}
                        />
                      </div>
                    </div>

                    <p className="section-divider">Inverse DCT converts modified frequencies back into pixel values</p>

                    <div className="legend-card">
                      <h4>Color Meaning</h4>
                      <p><i className="legend-dot green" /> Green: embedding positions</p>
                      <p><i className="legend-dot red" /> Red: modified values</p>
                      <p><i className="legend-dot blue" /> Blue: unchanged values</p>
                    </div>

                    <p className="muted-note">We do not modify pixels directly; we modify frequency components.</p>
                    <p className="muted-note">Small changes in frequency domain result in minimal visible changes in the image.</p>
                    <p className="muted-note">Embedding is distributed across multiple blocks in the full image.</p>
                  </div>
                )}

                {Array.isArray(embeddingDebug.sample_operations) && embeddingDebug.sample_operations.length > 0 && (
                  <div className="ops-table-wrap">
                    <p className="label">Intermediate embedding operations (sample)</p>
                    <p className="muted-note">
                      This table shows only the selected embedding coefficients, not the full DCT matrix.
                      Coeff after can be 0 when quantization snaps a small coefficient to the nearest valid bin.
                    </p>
                    <div className="ops-table-wrap-scroll">
                      <table className="ops-table">
                        <thead>
                          <tr>
                            <th>bit#</th>
                            <th>block(r,c)</th>
                            <th>dct(u,v)</th>
                            <th>bit</th>
                            <th>coeff before</th>
                            <th>coeff after</th>
                            <th title="Change applied to encode bit">delta</th>
                            <th>q-index b/a</th>
                            <th>modified?</th>
                          </tr>
                        </thead>
                        <tbody>
                          {embeddingDebug.sample_operations.map((op) => (
                            <tr key={`row-${op.payload_bit_index}`} className={op.was_modified ? "changed-row" : ""}>
                              <td>{op.payload_bit_index}</td>
                              <td>{op.block_row},{op.block_col}</td>
                              <td>{op.dct_position[0]},{op.dct_position[1]}</td>
                              <td>{op.embedded_bit}</td>
                              <td>{op.coeff_before}</td>
                              <td>{op.coeff_after}</td>
                              <td>{op.coeff_delta}</td>
                              <td>{op.q_index_before} / {op.q_index_after}</td>
                              <td>{op.was_modified ? "yes" : "no"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <div className="panel-subtle summary-box">
                  <h4>Embedding Summary:</h4>
                  <p>- Signature converted to binary</p>
                  <p>- Bits embedded in DCT coefficients</p>
                  <p>- Image reconstructed using inverse DCT</p>
                  <p>- Visual quality preserved</p>
                </div>

                <div className="insight-box">
                  <h4>Key Insight</h4>
                  <p>
                    Data is not stored in pixels directly, but in frequency patterns, making it robust to compression
                    and invisible to humans.
                  </p>
                </div>
              </div>
            )}

            {signResult?.embedding_info && (
              <p>
                <strong>Method:</strong> {signResult.embedding_info.method} | <strong>Description:</strong>{" "}
                {signResult.embedding_info.description}
              </p>
            )}

            <p className="muted-note">
              This embedded signature will later be extracted and verified using a public key.
            </p>
          </StepCard>

          <StepCard
            title="Step 5: Signed Image"
            explain="The signature-embedded image is exported as a signed PNG."
            active={currentStep >= 5}
          >
            {signResult?.signed_image ? (
              <>
                <img src={signedImageUrl} alt="Signed output" className="image-preview" />
                <a className="action-button inline" href={signedImageUrl} download="signed_image.png">
                  Download signed image
                </a>
              </>
            ) : (
              <p>Signed image preview appears here.</p>
            )}
          </StepCard>
        </div>

        {error && <p className="error-text">{error}</p>}

        <section className="panel-card process-summary">
          <h3>Process Summary</h3>
          <ol>
            <li>Image -&gt; Hash (SHA-256)</li>
            <li>Hash -&gt; Signature (ECDSA)</li>
            <li>Signature -&gt; Binary bits</li>
            <li>Bits -&gt; Embedded in DCT coefficients</li>
            <li>Output -&gt; Signed Image</li>
          </ol>
        </section>
      </section>
    </main>
  );
}

export default App;
