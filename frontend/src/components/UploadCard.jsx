import { useEffect, useState } from "react";

function UploadCard({ label, file, onFileSelected, onSubmit, busy, buttonText }) {
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return undefined;
    }

    const nextUrl = URL.createObjectURL(file);
    setPreviewUrl(nextUrl);

    return () => {
      URL.revokeObjectURL(nextUrl);
    };
  }, [file]);

  const handleDrop = (event) => {
    event.preventDefault();
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) {
      onFileSelected(dropped);
    }
  };

  return (
    <div className="panel-card">
      <h3>{label}</h3>
      <label
        className="drop-zone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept="image/*"
          onChange={(event) => onFileSelected(event.target.files?.[0] || null)}
        />
        <span>Drag and drop an image, or click to browse</span>
      </label>

      {previewUrl && (
        <div className="preview-wrap">
          <img src={previewUrl} alt="Uploaded preview" className="image-preview" />
        </div>
      )}

      <button className="action-button" disabled={!file || busy} onClick={onSubmit}>
        {busy ? "Processing..." : buttonText}
      </button>
    </div>
  );
}

export default UploadCard;
