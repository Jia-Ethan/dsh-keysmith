import React from "react";
import { useTranslation } from "react-i18next";
import { open } from "@tauri-apps/plugin-dialog";
import { toast } from "sonner";
import { ChevronRight } from "lucide-react";
import { useAppState } from "@/hooks/useAppState";
import { getSettings } from "@/lib/settings";
import { previewDeploy, executeDeploy } from "@/lib/api";
import { FadeIn } from "@/components/FadeIn";
import { ReportView } from "@/components/ReportView";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { setLastStatus, setView } from "@/lib/store";

function StepHeader({ step }) {
  const { t } = useTranslation();
  const steps = ["step1", "step2", "step3"];
  return (
    <ol className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
      {steps.map((key, index) => (
        <li key={key} className="flex items-center gap-1.5">
          <span className={cn(
            "inline-flex size-5 items-center justify-center rounded-full border text-[10px] font-medium",
            index + 1 === step
              ? "border-accent bg-accent text-white"
              : index + 1 < step
                ? "border-[var(--ok)] text-ok"
                : "border-border text-muted-foreground",
          )}>
            {index + 1}
          </span>
          <span className={index + 1 === step ? "font-medium text-foreground" : "text-muted-foreground"}>
            {t(`deploy.${key}`)}
          </span>
          {index < steps.length - 1 && <ChevronRight className="size-3 text-muted-foreground" aria-hidden="true" />}
        </li>
      ))}
    </ol>
  );
}

export function Deploy() {
  const { t } = useTranslation();
  const { cliInfo, operationInProgress } = useAppState();
  const [step, setStep] = React.useState(1);
  const [source, setSource] = React.useState("bundled");
  const [filePath, setFilePath] = React.useState("");
  const [name, setName] = React.useState("");
  const [dshDir, setDshDir] = React.useState(() => getSettings().defaultDshDir || "");
  const [preview, setPreview] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  const options = {
    file: source === "file" ? filePath.trim() : "",
    name: name.trim(),
    dshDir: dshDir.trim(),
  };
  const canPreview = source === "bundled" || Boolean(filePath.trim());

  const runPreview = async () => {
    setBusy(true);
    try {
      const report = await previewDeploy(options);
      setPreview(report);
      setStep(2);
    } catch (err) {
      toast.error(err?.message || t("deploy.previewFailed"));
    } finally {
      setBusy(false);
    }
  };

  const runExecute = async () => {
    setBusy(true);
    try {
      const report = await executeDeploy(options);
      setPreview(report);
      setConfirmOpen(false);
      if (report.gate.ok) {
        toast.success(t("deploy.success"));
        setLastStatus(null);
        setTimeout(() => setView("dashboard"), 800);
      } else {
        toast.error(t("deploy.failed"));
      }
    } catch (err) {
      toast.error(err?.message || t("deploy.failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <FadeIn>
        <h1 className="text-2xl font-semibold tracking-tight">{t("deploy.title")}</h1>
        <StepHeader step={step} />
      </FadeIn>

      {step === 1 && (
        <FadeIn className="mt-6 space-y-4">
          <section className="card-glass p-5">
            <div className="text-sm font-medium">{t("deploy.source")}</div>
            <div className="mt-2 flex gap-2">
              <Button size="sm" variant={source === "bundled" ? "default" : "secondary"} onClick={() => setSource("bundled")}>
                {t("deploy.sourceBundled")}
              </Button>
              <Button size="sm" variant={source === "file" ? "default" : "secondary"} onClick={() => setSource("file")}>
                {t("deploy.sourceFile")}
              </Button>
            </div>
            {source === "file" && (
              <div className="mt-3 flex gap-2">
                <Input className="flex-1 font-mono text-xs" value={filePath} onChange={(e) => setFilePath(e.target.value)} placeholder={t("deploy.noFile")} />
                <Button variant="outline" onClick={async () => {
                  const picked = await open({ filters: [{ name: "Markdown", extensions: ["md"] }] });
                  if (picked) setFilePath(picked);
                }}>{t("deploy.pickFile")}</Button>
              </div>
            )}
            <label className="mt-4 block text-sm font-medium" htmlFor="deploy-name">{t("deploy.name")}</label>
            <Input id="deploy-name" className="mt-1.5 font-mono text-xs" value={name} onChange={(e) => setName(e.target.value)} placeholder={t("deploy.namePlaceholder")} />
            <label className="mt-4 block text-sm font-medium" htmlFor="deploy-dir">{t("deploy.targetDir")}</label>
            <div className="mt-1.5 flex gap-2">
              <Input id="deploy-dir" className="flex-1 font-mono text-xs" value={dshDir} onChange={(e) => setDshDir(e.target.value)} placeholder={t("deploy.targetDirPlaceholder")} />
              <Button variant="outline" onClick={async () => {
                const picked = await open({ directory: true });
                if (picked) setDshDir(picked);
              }}>{t("deploy.pickDir")}</Button>
            </div>
          </section>
          <Button disabled={!canPreview || busy || !cliInfo.path || operationInProgress} onClick={runPreview}>
            {t("deploy.next")}
          </Button>
        </FadeIn>
      )}

      {step >= 2 && preview && (
        <FadeIn className="mt-6">
          <section className="card-glass p-5">
            <ReportView report={preview} showTarget={false} />
          </section>
          <div className="mt-4 flex gap-2">
            <Button variant="secondary" onClick={() => setStep(1)}>{t("deploy.back")}</Button>
            <Button disabled={!preview.gate.ok || busy} onClick={() => { setStep(3); setConfirmOpen(true); }}>
              {t("deploy.confirmDeploy")}
            </Button>
          </div>
        </FadeIn>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("deploy.confirmDeploy")}
        body={t("deploy.confirmHint")}
        confirmText={t("common.confirm")}
        confirmDisabled={busy}
        onConfirm={runExecute}
      />
    </div>
  );
}
