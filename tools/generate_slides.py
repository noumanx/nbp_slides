import sys
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time

# Import gemini_generate_image from the same directory
import gemini_generate_image

def parse_slides(outline_path, start_slide=1, end_slide=19):
    with open(outline_path, 'r') as f:
        content = f.read()
    
    slides = []
    # Regex to find slide blocks
    slide_pattern = re.compile(r'#### Slide (\d+):(.*?)(?=#### Slide \d+:|$)', re.DOTALL)
    
    matches = slide_pattern.finditer(content)
    for match in matches:
        slide_num = int(match.group(1))
        if start_slide <= slide_num <= end_slide:
            slide_content = match.group(0).strip()
            
            # Extract Asset paths
            asset_paths = []
            
            # Find the Asset section
            # matches * **Asset**: or * **Asset:** or * **Asset** :
            asset_header_match = re.search(r'\*\s+\*\*Asset\*\*?\s*:?', slide_content)
            
            if asset_header_match:
                # Get the text following the header
                rest_of_section = slide_content[asset_header_match.end():]
                
                # Split into lines
                lines = rest_of_section.split('\n')
                
                # Check the first line (if content is on the same line as **Asset**:)
                current_line = lines[0].strip()
                if current_line and current_line.lower() != "none":
                    asset_paths.append(current_line)
                
                # Process subsequent lines looking for bullet points
                for line in lines[1:]:
                    stripped = line.strip()
                    if not stripped:
                        continue
                        
                    # Stop if we hit a new major section (indicated by * **Key**:)
                    if re.match(r'^\*\s+\*\*', stripped) and not stripped.startswith('* **Asset'):
                         break
                    
                    # Check for list items
                    if stripped.startswith('* ') or stripped.startswith('- '):
                        val = stripped[2:].strip()
                        if val.lower() != "none":
                            asset_paths.append(val)

            slides.append({
                'number': slide_num,
                'content': slide_content,
                'asset_paths': asset_paths
            })
    return slides

def generate_slide(slide, guideline, output_dir, project_root):
    print(f"Starting generation for Slide {slide['number']}...")
    
    prompt = f"""
    You are an expert presentation designer for a high-end tech keynote.
    
    VISUAL GUIDELINES (MUST FOLLOW):
    {guideline}
    
    SLIDE CONTENT:
    {slide['content']}
    
    TASK:
    Generate a high-resolution, 16:9 slide image that perfectly represents the content above while strictly adhering to the visual guidelines. 
    The image should be the final slide itself, including any text or graphical elements described.
    Make it look like a professional slide from a Keynote presentation.
    """
    
    image_inputs = []
    if slide.get('asset_paths'):
        for path_str in slide['asset_paths']:
            # Resolve asset path relative to project root
            if not os.path.isabs(path_str):
                asset_path = project_root / path_str
            else:
                asset_path = Path(path_str)
            
            if asset_path.exists():
                print(f"  Using asset: {asset_path}")
                prompt += f"\n    NOTE: Incorporate the provided reference image ({asset_path.name}) into the design as described."
                image_inputs.append(str(asset_path))
            else:
                print(f"  WARNING: Asset file not found at {asset_path}. Skipping this asset.")

    output_filename = os.path.join(str(output_dir), f"slide_{slide['number']:02d}")
    
    try:
        gemini_generate_image.generate(
            prompt=prompt,
            image_paths=image_inputs if image_inputs else None,
            output_prefix=output_filename,
            image_size="2K", 
            aspect_ratio="16:9"
        )
        print(f"Finished Slide {slide['number']}")
    except Exception as e:
        print(f"Error generating Slide {slide['number']}: {e}")

def main():
    # Get project root directory (parent of tools directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    outline_path = project_root / "outline_visual.md"
    guideline_path = project_root / "visual_guideline.md"
    output_dir = project_root / "generated_slides"
    
    os.makedirs(output_dir, exist_ok=True)
    
    with open(guideline_path, 'r') as f:
        guideline = f.read()
        
    # Generate only slide 8 as requested
    slides = parse_slides(str(outline_path), 8, 8) 
    
    print(f"Found {len(slides)} slides to generate.")
    
    with ThreadPoolExecutor(max_workers=4) as executor: 
        futures = [
            executor.submit(generate_slide, slide, guideline, output_dir, project_root)
            for slide in slides
        ]
        
        for future in futures:
            future.result()

if __name__ == "__main__":
    main()
