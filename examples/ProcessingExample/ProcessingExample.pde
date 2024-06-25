import oscP5.*;
import netP5.*;

OscP5 oscP5;
ArrayList<TuioTag> tuioTags = new ArrayList<TuioTag>();
ArrayList<TuioTag> toAdd = new ArrayList<TuioTag>();

void setup() {
  size(800, 600);
  oscP5 = new OscP5(this, 3334); // Listen on port 3333
}

void draw() {
  background(0);
  for (TuioTag tag : tuioTags) {
    tag.display();
  }
  tuioTags.addAll(toAdd);
  toAdd.removeAll(toAdd);
}

void oscEvent(OscMessage theOscMessage) {

  try {
   // print(" addrpattern: "+theOscMessage.get(0));
    String jsonString = theOscMessage.get(0).stringValue();
    JSONObject json = JSONObject.parse(jsonString);
    int tagId = json.getInt("tagid");
    String change = json.getString("change");

    if (change.equals("moved") || change.equals("added")) {
      float xpos = json.getFloat("xpos");
      float ypos = json.getFloat("ypos");
      float angle = json.getFloat("ang");
      float xvel = json.getFloat("xvel");
      float yvel = json.getFloat("yvel");
      float angvel = json.getFloat("angvel");
      TuioTag tag = findTagById(tagId);
      
      if (tag == null) {
        tag = new TuioTag(tagId, xpos, ypos, angle);
        toAdd.add(tag);
      } else {
        tag.setVisible(true);
        tag.update(xpos, ypos, angle);
      }
    } else if (change.equals("disappeared")) {
      TuioTag tag = findTagById(tagId);
      if (tag != null) {
        tag.setVisible(false);
      }
    }
  }
  catch (Exception e) {
    println("Error parsing JSON: " + e.getMessage());
  }
}


TuioTag findTagById(int id) {
  for (TuioTag tag : tuioTags) {
    if (tag.id == id) {
      return tag;
    }
  }
  return null;
}

class TuioTag {
  int id;
  float x, y, angle, xAverage, yAverage, angleAverage, displayAngle;
  boolean visible;

  TuioTag(int id, float x, float y, float angle) {
    this.id = id;
    this.x = x * width;
    this.y = y * height;
    this.angle = angle;
    this.xAverage = this.x;
    this.yAverage = this.y;
    this.angleAverage = this.angle;
    this.displayAngle = this.angle;
    this.visible = true;
  }

  void update(float xpos, float ypos, float newAngle) {
    this.x = xpos * width;
    this.y = ypos * height;
    this.angle = newAngle;
  }

  void setVisible(boolean set) {
    this.visible = set;
  }
  void display() {
    if (this.visible) {
    // smooth out position and angle
    float factor = 0.95f;
    this.xAverage = this.xAverage*factor;
    this.xAverage += this.x*(1.0f-factor);

    this.yAverage = this.yAverage*factor;
    this.yAverage += this.y*(1.0f-factor);


    float delta = (TWO_PI - (this.angleAverage-this.angle))% TWO_PI;

    if (delta > PI) {
      delta = (TWO_PI-delta);
      this.angleAverage = this.angleAverage - delta;
    } else {
      delta = (TWO_PI+delta);
      this.angleAverage = this.angleAverage + delta;
    }

    pushMatrix();
    translate(this.xAverage, this.yAverage);
    rotate(this.angleAverage);
    noStroke();
    fill(255, 255, 0);
    ellipse(0, 0, 40, 40);
    fill(0);
    textAlign(CENTER, CENTER);
    text(id, 0, 0);
    popMatrix();
  }
  }
}
