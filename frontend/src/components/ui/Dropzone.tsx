import { useRef, useState } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { UploadCloud, X } from 'lucide-react';
import { clsx } from 'clsx';

export function Dropzone({ files, onChange }: { files: File[], onChange: (files: File[]) => void }) {
    const [isDragging, setIsDragging] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDragOver = (e: DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files) {
            handleFiles(Array.from(e.dataTransfer.files));
        }
    };

    const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            handleFiles(Array.from(e.target.files));
        }
    };

    const handleFiles = (newFiles: File[]) => {
        // В реальности здесь была бы проверка на размер (до 10 МБ) и тип (JPG/PNG)
        const validFiles = newFiles.filter(f => f.type.startsWith('image/'));
        onChange([...files, ...validFiles].slice(0, 10)); // Максимум 10 файлов
    };

    const removeFile = (index: number) => {
        onChange(files.filter((_, i) => i !== index));
    };

    return (
        <div className="space-y-4">
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                className={clsx(
                    "border-2 border-dashed rounded-card p-8 flex flex-col items-center justify-center cursor-pointer transition-colors bg-field",
                    isDragging ? "border-accent bg-accent-soft" : "border-border hover:border-accent/50"
                )}
            >
                <input type="file" multiple accept="image/jpeg, image/png" className="hidden" ref={inputRef} onChange={handleFileInput} />

                <UploadCloud size={32} className="text-accent mb-3" />
                <p className="font-medium text-accent mb-1">Загрузите фото дефекта или перетащите файлы</p>
                <p className="text-xs text-muted">До 10 фото · JPG, PNG · до 10 МБ</p>
            </div>

            {files.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {files.map((file, i) => (
                        <div key={i} className="relative group rounded-lg border border-border overflow-hidden bg-white aspect-square flex items-center justify-center">
                            <img src={URL.createObjectURL(file)} alt="preview" className="object-cover w-full h-full" />
                            <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                                className="absolute top-2 right-2 p-1 bg-white/90 rounded-full text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm hover:bg-red-50"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}