"""Draw Motion API — Physical Motion System.

Controls rigid bodies, particles, and physical presets through foundational
physical quantities: mass, position, velocity, acceleration, force, rotation,
angular velocity, torque, moment of inertia, restitution, friction, drag, and gravity.
"""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from .vector import Vector2D, PointLike, vec2


class PhysicalBody:
    """Rigid body physics entity with mass, inertia, state, and collision properties.

    Attributes:
        mass: Body mass in kg (0.0 represents static/immovable body).
        position: Current 2D position vector (m or px).
        velocity: Current linear velocity vector (m/s).
        acceleration: Current linear acceleration vector (m/s²).
        force: Accumulated external forces (N).
        rotation: Orientation in radians.
        angular_velocity: Rotational speed in rad/s.
        torque: Accumulated rotational torque in N·m.
        inertia: Moment of inertia in kg·m².
        restitution: Coefficient of restitution (bounce, 0.0–1.0).
        friction: Coefficient of friction (sliding resistance, 0.0–1.0).
        drag: Medium resistance coefficient (0.0–1.0).
        density: Mass density.
        gravity: Gravitational acceleration vector (default: (0.0, -9.8)).
        radius: Collision radius for bounding sphere / circle tests.
    """

    def __init__(
        self,
        mass: float = 1.0,
        position: PointLike = (0.0, 0.0),
        velocity: PointLike = (0.0, 0.0),
        acceleration: PointLike = (0.0, 0.0),
        force: PointLike = (0.0, 0.0),
        rotation: float = 0.0,
        angular_velocity: float = 0.0,
        torque: float = 0.0,
        inertia: Optional[float] = None,
        restitution: float = 0.8,
        friction: float = 0.1,
        drag: float = 0.0,
        density: float = 1.0,
        gravity: PointLike = (0.0, -9.8),
        radius: float = 10.0,
    ) -> None:
        self.mass: float = max(0.0, float(mass))
        self.inv_mass: float = 1.0 / self.mass if self.mass > 1e-12 else 0.0

        self.position: Vector2D = Vector2D.from_value(position)
        self.velocity: Vector2D = Vector2D.from_value(velocity)
        self.acceleration: Vector2D = Vector2D.from_value(acceleration)
        self.force: Vector2D = Vector2D.from_value(force)

        self.rotation: float = float(rotation)
        self.angular_velocity: float = float(angular_velocity)
        self.torque: float = float(torque)

        # Default moment of inertia: disk / cylinder I = 0.5 * m * r^2
        self.radius: float = float(radius)
        if inertia is not None:
            self.inertia: float = max(0.0, float(inertia))
        else:
            self.inertia = 0.5 * self.mass * (self.radius * self.radius) if self.mass > 0 else 0.0
        self.inv_inertia: float = 1.0 / self.inertia if self.inertia > 1e-12 else 0.0

        self.restitution: float = max(0.0, min(1.0, float(restitution)))
        self.friction: float = max(0.0, float(friction))
        self.drag: float = max(0.0, float(drag))
        self.density: float = float(density)
        self.gravity: Vector2D = Vector2D.from_value(gravity)

    # ── Required Physical Methods ───────────────────────────────────────

    def apply_force(self, f: PointLike) -> None:
        """Applies external continuous force to body (accumulated per step)."""
        self.force += Vector2D.from_value(f)

    def apply_impulse(self, impulse: PointLike) -> None:
        """Applies instantaneous change in momentum: delta_v = impulse / mass."""
        if self.inv_mass > 0.0:
            self.velocity += Vector2D.from_value(impulse) * self.inv_mass

    def apply_torque(self, t: float) -> None:
        """Applies rotational torque in N·m (accumulated per step)."""
        self.torque += float(t)

    def set_velocity(self, velocity: PointLike) -> None:
        """Directly sets linear velocity."""
        self.velocity = Vector2D.from_value(velocity)

    def set_acceleration(self, acceleration: PointLike) -> None:
        """Directly sets linear acceleration."""
        self.acceleration = Vector2D.from_value(acceleration)

    def integrate(self, dt: float) -> None:
        """Updates position and linear velocity via semi-implicit Euler integration."""
        if self.inv_mass <= 0.0:
            return

        dt = float(dt)
        # Total acceleration = applied acceleration + (forces / mass) + gravity
        total_acc = self.acceleration + self.gravity + (self.force * self.inv_mass)

        # Apply medium drag
        if self.drag > 0.0:
            speed = self.velocity.length()
            if speed > 1e-12:
                drag_force = -self.velocity.normalize() * (0.5 * self.drag * speed * speed)
                total_acc += drag_force * self.inv_mass

        # Update velocity & position
        self.velocity += total_acc * dt
        self.position += self.velocity * dt

        # Reset accumulated forces
        self.force = Vector2D(0.0, 0.0)

    def integrate_rotation(self, dt: float) -> None:
        """Updates orientation and angular velocity."""
        if self.inv_inertia <= 0.0:
            return

        dt = float(dt)
        angular_acc = self.torque * self.inv_inertia

        # Angular drag
        if self.drag > 0.0:
            angular_acc -= self.angular_velocity * self.drag

        self.angular_velocity += angular_acc * dt
        self.rotation += self.angular_velocity * dt

        # Reset accumulated torque
        self.torque = 0.0

    def step(self, dt: float = 0.016) -> None:
        """Advances both linear and angular simulation by dt."""
        self.integrate(dt)
        self.integrate_rotation(dt)

    def calculate_momentum(self) -> Vector2D:
        """Calculates linear momentum p = m * v."""
        return self.velocity * self.mass

    def calculate_energy(self) -> float:
        """Calculates total kinetic energy: 0.5*m*v^2 + 0.5*I*omega^2."""
        linear_ke = 0.5 * self.mass * self.velocity.length_sq()
        rotational_ke = 0.5 * self.inertia * (self.angular_velocity * self.angular_velocity)
        return linear_ke + rotational_ke

    def detect_collision(self, other: "PhysicalBody") -> bool:
        """Detects circular collision intersection between two physical bodies."""
        min_dist = self.radius + other.radius
        return self.position.distance_sq_to(other.position) <= (min_dist * min_dist)

    def calculate_restitution(self, other: "PhysicalBody") -> float:
        """Calculates combined bounce coefficient (geometric mean)."""
        return math.sqrt(self.restitution * other.restitution)

    def calculate_friction(self, normal_force: float) -> float:
        """Calculates sliding friction force: F_f = mu * F_N."""
        return self.friction * abs(float(normal_force))

    def resolve_collision(self, other: "PhysicalBody") -> bool:
        """Calculates and applies 2D rigid body collision response with restitution and momentum."""
        delta = other.position - self.position
        dist = delta.length()
        min_dist = self.radius + other.radius

        if dist >= min_dist or dist < 1e-12:
            return False

        # Collision normal pointing from self to other
        normal = delta.normalize()

        # Relative velocity
        rel_vel = other.velocity - self.velocity
        vel_along_normal = rel_vel.dot(normal)

        # Do not resolve if velocities are separating
        if vel_along_normal > 0:
            return False

        # Combined restitution
        e = self.calculate_restitution(other)

        # Impulse scalar
        total_inv_mass = self.inv_mass + other.inv_mass
        if total_inv_mass < 1e-12:
            return False

        j = -(1.0 + e) * vel_along_normal / total_inv_mass
        impulse = normal * j

        # Apply impulse
        self.apply_impulse(-impulse)
        other.apply_impulse(impulse)

        # Positional correction to prevent overlap sinking
        percent = 0.4
        slop = 0.01
        penetration = min_dist - dist
        correction = normal * (max(penetration - slop, 0.0) / total_inv_mass * percent)
        if self.inv_mass > 0:
            self.position -= correction * self.inv_mass
        if other.inv_mass > 0:
            other.position += correction * other.inv_mass

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serializes physical body state for the C++/OpenGL engine."""
        return {
            "mass": self.mass,
            "position": self.position.to_list(),
            "velocity": self.velocity.to_list(),
            "acceleration": self.acceleration.to_list(),
            "force": self.force.to_list(),
            "rotation": round(self.rotation, 4),
            "angular_velocity": round(self.angular_velocity, 4),
            "torque": round(self.torque, 4),
            "inertia": round(self.inertia, 4),
            "restitution": round(self.restitution, 4),
            "friction": round(self.friction, 4),
            "drag": round(self.drag, 4),
            "density": round(self.density, 4),
            "gravity": self.gravity.to_list(),
            "radius": round(self.radius, 4),
        }

    def __repr__(self) -> str:
        return (
            f"PhysicalBody(mass={self.mass}, pos={self.position}, "
            f"vel={self.velocity}, acc={self.acceleration})"
        )


# ═══════════════════════════════════════════════════════════════════════
# PHYSICAL MOTION PRESETS (BUILT ON FOUNDATIONAL QUANTITIES)
# ═══════════════════════════════════════════════════════════════════════

def projectile(
    position: PointLike = (0.0, 0.0),
    velocity: PointLike = (20.0, 15.0),
    gravity: PointLike = (0.0, -9.8),
    mass: float = 1.0,
    drag: float = 0.0,
) -> PhysicalBody:
    """Projectile preset: body with initial velocity moving under constant gravity."""
    return PhysicalBody(
        mass=mass,
        position=position,
        velocity=velocity,
        gravity=gravity,
        drag=drag,
    )


def free_fall(
    position: PointLike = (0.0, 100.0),
    gravity: PointLike = (0.0, -9.8),
    mass: float = 1.0,
    drag: float = 0.0,
) -> PhysicalBody:
    """Free fall preset: stationary body falling under gravity."""
    return PhysicalBody(
        mass=mass,
        position=position,
        velocity=(0.0, 0.0),
        gravity=gravity,
        drag=drag,
    )


def circular(
    center: PointLike = (0.0, 0.0),
    radius: float = 50.0,
    angular_velocity: float = 1.0,
    mass: float = 1.0,
) -> PhysicalBody:
    """Circular motion preset: centripetal acceleration a = omega^2 * r."""
    pos = (float(center[0]) + radius, float(center[1]))
    # Tangential velocity v = omega * r perpendicular to radius
    vel = (0.0, angular_velocity * radius)
    body = PhysicalBody(
        mass=mass,
        position=pos,
        velocity=vel,
        angular_velocity=angular_velocity,
        gravity=(0.0, 0.0),
        radius=radius,
    )
    return body


def uniform_circular(
    center: PointLike = (0.0, 0.0),
    radius: float = 50.0,
    speed: float = 10.0,
    mass: float = 1.0,
) -> PhysicalBody:
    """Uniform circular motion preset: constant tangential speed."""
    omega = speed / radius if radius > 1e-6 else 0.0
    return circular(center=center, radius=radius, angular_velocity=omega, mass=mass)


def elliptical(
    center: PointLike = (0.0, 0.0),
    rx: float = 100.0,
    ry: float = 50.0,
    speed: float = 1.0,
    mass: float = 1.0,
) -> PhysicalBody:
    """Elliptical orbital motion preset."""
    body = PhysicalBody(
        mass=mass,
        position=(center[0] + rx, center[1]),
        velocity=(0.0, speed * (ry / rx if rx > 0 else 1.0)),
        gravity=(0.0, 0.0),
    )
    return body


def oscillation(
    amplitude: float = 50.0,
    frequency: float = 1.0,
    damping: float = 0.0,
    mass: float = 1.0,
) -> PhysicalBody:
    """Harmonic restoring force oscillation preset."""
    body = PhysicalBody(
        mass=mass,
        position=(amplitude, 0.0),
        velocity=(0.0, 0.0),
        gravity=(0.0, 0.0),
        drag=damping,
    )
    return body


def pendulum(
    length: float = 100.0,
    angle_deg: float = 30.0,
    gravity: float = 9.8,
    mass: float = 1.0,
) -> PhysicalBody:
    """Simple pendulum angular dynamics preset."""
    theta_rad = math.radians(angle_deg)
    pos_x = length * math.sin(theta_rad)
    pos_y = -length * math.cos(theta_rad)
    body = PhysicalBody(
        mass=mass,
        position=(pos_x, pos_y),
        velocity=(0.0, 0.0),
        rotation=theta_rad,
        gravity=(0.0, -gravity),
        radius=5.0,
    )
    return body


def spring(
    anchor: PointLike = (0.0, 100.0),
    stiffness: float = 10.0,
    rest_length: float = 50.0,
    damping: float = 0.5,
    mass: float = 1.0,
) -> PhysicalBody:
    """Hooke's law spring preset."""
    body = PhysicalBody(
        mass=mass,
        position=(anchor[0], anchor[1] - rest_length),
        velocity=(0.0, 0.0),
        gravity=(0.0, -9.8),
        drag=damping,
    )
    return body


def collision(body_a: PhysicalBody, body_b: PhysicalBody) -> bool:
    """Helper executing collision detection and response between two bodies."""
    if body_a.detect_collision(body_b):
        return body_a.resolve_collision(body_b)
    return False


def rolling(
    radius: float = 20.0,
    linear_velocity: float = 10.0,
    mass: float = 1.0,
) -> PhysicalBody:
    """Rolling preset with matching linear and angular velocities: omega = v / r."""
    omega = -linear_velocity / radius if radius > 1e-6 else 0.0
    return PhysicalBody(
        mass=mass,
        position=(0.0, radius),
        velocity=(linear_velocity, 0.0),
        angular_velocity=omega,
        radius=radius,
        friction=0.2,
    )


def sliding(
    velocity: PointLike = (20.0, 0.0),
    friction_coeff: float = 0.2,
    mass: float = 1.0,
) -> PhysicalBody:
    """Sliding block preset decelerating under contact friction."""
    return PhysicalBody(
        mass=mass,
        position=(0.0, 0.0),
        velocity=velocity,
        friction=friction_coeff,
        gravity=(0.0, -9.8),
    )


def bouncing(
    position: PointLike = (0.0, 100.0),
    velocity: PointLike = (5.0, 0.0),
    floor_y: float = 0.0,
    restitution: float = 0.8,
    gravity: PointLike = (0.0, -9.8),
    mass: float = 1.0,
) -> PhysicalBody:
    """Bouncing ball preset with restitution coefficient."""
    body = PhysicalBody(
        mass=mass,
        position=position,
        velocity=velocity,
        restitution=restitution,
        gravity=gravity,
        radius=10.0,
    )
    return body


# ═══════════════════════════════════════════════════════════════════════
# PHYSICAL TRANSFORM CONTAINER
# ═══════════════════════════════════════════════════════════════════════

class PhysicalTransform:
    """Container wrapping PhysicalBody state inside motion.transform(type='physical', ...)."""

    def __init__(
        self,
        mass: float = 1.0,
        position: PointLike = (0.0, 0.0),
        velocity: PointLike = (0.0, 0.0),
        acceleration: PointLike = (0.0, 0.0),
        force: PointLike = (0.0, 0.0),
        rotation: float = 0.0,
        angular_velocity: float = 0.0,
        torque: float = 0.0,
        inertia: Optional[float] = None,
        restitution: float = 0.8,
        friction: float = 0.1,
        drag: float = 0.0,
        density: float = 1.0,
        gravity: PointLike = (0.0, -9.8),
        preset: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.type: str = "physical"
        self.body: PhysicalBody = PhysicalBody(
            mass=mass,
            position=position,
            velocity=velocity,
            acceleration=acceleration,
            force=force,
            rotation=rotation,
            angular_velocity=angular_velocity,
            torque=torque,
            inertia=inertia,
            restitution=restitution,
            friction=friction,
            drag=drag,
            density=density,
            gravity=gravity,
            radius=float(kwargs.get("radius", 10.0)),
        )
        self.preset: Optional[str] = preset
        self.extra_params: Dict[str, Any] = kwargs

    @property
    def mass(self) -> float:
        return self.body.mass

    @property
    def position(self) -> Vector2D:
        return self.body.position

    @property
    def velocity(self) -> Vector2D:
        return self.body.velocity

    @property
    def acceleration(self) -> Vector2D:
        return self.body.acceleration

    @property
    def force(self) -> Vector2D:
        return self.body.force

    @property
    def rotation(self) -> float:
        return self.body.rotation

    @property
    def angular_velocity(self) -> float:
        return self.body.angular_velocity

    @property
    def torque(self) -> float:
        return self.body.torque

    @property
    def inertia(self) -> float:
        return self.body.inertia

    def step(self, dt: float = 0.016) -> None:
        """Simulates physical time step."""
        self.body.step(dt)

    def apply_force(self, f: PointLike) -> None:
        self.body.apply_force(f)

    def apply_impulse(self, impulse: PointLike) -> None:
        self.body.apply_impulse(impulse)

    def apply_torque(self, t: float) -> None:
        self.body.apply_torque(t)

    def set_velocity(self, velocity: PointLike) -> None:
        self.body.set_velocity(velocity)

    def set_acceleration(self, acceleration: PointLike) -> None:
        self.body.set_acceleration(acceleration)

    def integrate(self, dt: float) -> None:
        self.body.integrate(dt)

    def integrate_rotation(self, dt: float) -> None:
        self.body.integrate_rotation(dt)

    def calculate_momentum(self) -> Vector2D:
        return self.body.calculate_momentum()

    def calculate_energy(self) -> float:
        return self.body.calculate_energy()

    def detect_collision(self, other: Union[PhysicalBody, "PhysicalTransform"]) -> bool:
        other_body = other.body if isinstance(other, PhysicalTransform) else other
        return self.body.detect_collision(other_body)

    def resolve_collision(self, other: Union[PhysicalBody, "PhysicalTransform"]) -> bool:
        other_body = other.body if isinstance(other, PhysicalTransform) else other
        return self.body.resolve_collision(other_body)

    def calculate_restitution(self, other: Union[PhysicalBody, "PhysicalTransform"]) -> float:
        other_body = other.body if isinstance(other, PhysicalTransform) else other
        return self.body.calculate_restitution(other_body)

    def calculate_friction(self, normal_force: float) -> float:
        return self.body.calculate_friction(normal_force)

    def to_dict(self) -> Dict[str, Any]:
        data = self.body.to_dict()
        data["type"] = "physical"
        if self.preset:
            data["preset"] = self.preset
        return data

    def __repr__(self) -> str:
        return f"PhysicalTransform(body={self.body!r})"
