const fs = require('fs');
const path = require('path');
const JavaScriptObfuscator = require('javascript-obfuscator');

const srcDir = path.join(__dirname, 'static', 'js_src');
const destDir = path.join(__dirname, 'static', 'js');

if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
}

const files = fs.readdirSync(srcDir);

files.forEach(file => {
    if (file.endsWith('.js')) {
        const srcPath = path.join(srcDir, file);
        const destPath = path.join(destDir, file);
        
        const code = fs.readFileSync(srcPath, 'utf8');
        
        console.log(`Obfuscating ${file}...`);
        
        const obfuscatedResult = JavaScriptObfuscator.obfuscate(code, {
            compact: true,
            controlFlowFlattening: true,
            controlFlowFlatteningThreshold: 0.75,
            numbersToExpressions: true,
            simplify: true,
            stringArray: true,
            stringArrayEncoding: ['base64'],
            stringArrayThreshold: 0.75,
            splitStrings: true,
            splitStringsChunkLength: 10
        });
        
        fs.writeFileSync(destPath, obfuscatedResult.getObfuscatedCode(), 'utf8');
    }
});

console.log('All JS files obfuscated successfully!');
