# Project Overview

mpostele is a local, open-source pipeline for generating animated product videos and short-form marketing content from product screenshots, web pages, and generated voiceover.

## Objective

Build a workflow that can create polished, animated promotional clips entirely on a modest laptop without requiring expensive GPU rentals or heavy cloud infrastructure.

## Design constraints

- GTX 1050 Ti with 4GB VRAM
- 8GB system RAM
- offline-first operation
- open-source tools only
- emphasis on motion graphics and compositing rather than diffusion-based video synthesis

## Primary approach

The system uses a sequential production flow:

1. capture product UI or screenshots
2. generate motion overlays and animated elements
3. add voiceover and timing
4. composite the final video
5. export for social platforms

## Why not heavy video models

Large local AI video generation models often require 8GB to 12GB or more of VRAM for just a few seconds of output. That makes them a poor fit for this hardware profile. Instead, this project favors lightweight methods such as:

- FFmpeg motion filters
- Manim for programmatic animation
- Playwright CSS and JS animation
- compositing of still images and overlays

## Project outcome

The target is a repeatable pipeline that can produce:

- product reveal videos
- feature highlight clips
- landing-page animated previews
- vertical video exports for Shorts, Reels, and TikTok
