interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
}

export function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <label className="inline-flex items-center cursor-pointer gap-2" title={label}>
      <div className="relative">
        <input
          type="checkbox"
          className="sr-only peer"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div className="w-9 h-5 bg-bg-tertiary rounded-full peer-checked:bg-success transition-colors" />
        <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-text-secondary rounded-full transition-transform peer-checked:translate-x-4 peer-checked:bg-white" />
      </div>
      {label && <span className="text-xs text-text-muted">{label}</span>}
    </label>
  );
}
