### 1. src/screen.spec.tsx:166: the same render helper is copied into two spec files

Cost: a new provider has to be added to both copies.

Fix: move `renderScreen` into `test/render.tsx` and import it from both specs.

> function renderScreen(props: Props) {
>   return render(<Providers><Screen {...props} /></Providers>);
> }
> ...
> function renderEditor(props: Props) {
>   return render(<Providers><Editor {...props} /></Providers>);
> }

### 2. src/widgets/Editor.tsx:178: the font size is clamped in the editor and again in the bar

Cost: changing the limits means editing two files that must agree.

Fix: export `clampFontSize` from the bar and call it from the editor.

> Editor.tsx: `const size = Math.min(Math.max(value, 8), 96);`
> Bar.tsx: `const size = Math.min(Math.max(next, 8), 96);`

END OF ROUND
